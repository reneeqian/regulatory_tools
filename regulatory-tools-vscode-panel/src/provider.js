'use strict';
const vscode = require('vscode');
const fs = require('fs');
const path = require('path');

const SHARED = path.join(__dirname, '../../../forge/forge-vscode-panel/src/shared.js');
const {
  loadingHtml, errorHtml, wrapHtml, escHtml,
  resolveForge, resolveProjectPython, discoverCondaEnvs, gatherRepoMeta,
  buildRepoOverview, buildHealthCard,
} = require(SHARED);

// ── Constants ──────────────────────────────────────────────────────────────────

const CODE_MARKERS = ['pyproject.toml', 'setup.py', 'package.json', 'Cargo.toml', 'go.mod'];

// ── Provider ──────────────────────────────────────────────────────────────────

class RegulatoryWebviewProvider {
  static viewType = 'regulatorySidebar';

  constructor(extensionUri) {
    this._extensionUri = extensionUri;
    this._view = null;
    this._cachedHtml = null;
  }

  resolveWebviewView(webviewView) {
    this._view = webviewView;
    webviewView.webview.options = { enableScripts: true };
    webviewView.webview.html = loadingHtml('Initialising…');

    webviewView.webview.onDidReceiveMessage(msg => {
      if (msg.command === 'openExternal') {
        vscode.env.openExternal(vscode.Uri.parse(msg.url));
      }
      if (msg.command === 'setPrimaryRepo') {
        const cfg = vscode.workspace.getConfiguration('regulatory');
        cfg.update('primaryRepo', msg.name ?? '', vscode.ConfigurationTarget.Global)
          .then(() => this.refresh());
      }
      if (msg.command === 'generateDhf') {
        const roles = this._resolveRepos();
        const docsRepo = roles?.docs.find(r => r.name === msg.docsRepoName);
        if (docsRepo) this._runGenerateDhf(docsRepo.local_path, docsRepo.name, roles.primary);
      }
    });

    webviewView.onDidChangeVisibility(() => {
      if (webviewView.visible) {
        if (this._cachedHtml) {
          webviewView.webview.html = this._cachedHtml;
        } else {
          this.refresh();
        }
      }
    });

    this.refresh();
  }

  refresh() {
    if (!this._view) return;
    this._cachedHtml = null;
    this._view.webview.html = loadingHtml('Running regulatory checks…');
    this._run().catch(err => {
      if (this._view) this._view.webview.html = errorHtml(err.message);
    });
  }

  // ── Repo discovery ────────────────────────────────────────────────────────────

  _detectRepoType(localPath) {
    for (const marker of CODE_MARKERS) {
      if (fs.existsSync(path.join(localPath, marker))) return 'code';
    }
    const srcDir = path.join(localPath, 'src');
    if (fs.existsSync(srcDir)) {
      const files = fs.readdirSync(srcDir);
      if (files.some(f => /\.(py|js|ts|rb|java|cpp|go|rs)$/.test(f))) return 'code';
    }
    return 'docs';
  }

  _resolveRepos() {
    const folders = vscode.workspace.workspaceFolders ?? [];
    if (!folders.length) return null;

    const repos = folders.map(f => ({
      name: f.name,
      local_path: f.uri.fsPath,
      repoType: this._detectRepoType(f.uri.fsPath),
    }));

    const codeRepos = repos.filter(r => r.repoType === 'code');
    const docsRepos = repos.filter(r => r.repoType === 'docs');

    const primarySetting = vscode.workspace.getConfiguration('regulatory').get('primaryRepo', '');
    let primary = null;

    if (primarySetting) {
      primary = codeRepos.find(r => r.name === primarySetting) ?? null;
    } else if (codeRepos.length === 1) {
      primary = codeRepos[0];
    }

    const supporting = codeRepos.filter(r => r !== primary);

    return { primary, supporting, docs: docsRepos, all: repos };
  }

  // ── Main runner ───────────────────────────────────────────────────────────────

  async _run() {
    const folders = vscode.workspace.workspaceFolders ?? [];
    if (!folders.length) {
      throw new Error(
        'No folders are open in this VS Code workspace.\n\n' +
        'Open a folder or .code-workspace file to use the Regulatory Dashboard.'
      );
    }

    const roles = this._resolveRepos();
    const codeRepos = [
      ...(roles.primary ? [roles.primary] : []),
      ...roles.supporting,
    ];

    const primaryPath = roles.primary?.local_path ?? null;

    // Parse traceability for every code repo so supporting repos also show req coverage.
    const traceMap = {};
    for (const repo of codeRepos) {
      traceMap[repo.name] = this._parseTraceabilityMatrix(repo.local_path);
    }
    const artifactCheck = primaryPath ? this._checkRequiredArtifacts(primaryPath) : null;

    // Async health + meta in parallel.
    const forgePath = resolveForge();
    const q = s => `"${s}"`;

    const repoPythonInfo = {};
    for (const repo of codeRepos) {
      repoPythonInfo[repo.name] = resolveProjectPython(repo.name, repo.local_path);
    }

    const { execCmd } = require(SHARED);
    const [condaEnvs, metaMap, ...healthArr] = await Promise.all([
      discoverCondaEnvs(),
      gatherRepoMeta(codeRepos),
      ...codeRepos.map(repo => {
        const { python } = repoPythonInfo[repo.name];
        const pythonFlag = python ? `--python ${q(python)}` : '';
        return execCmd(`${q(forgePath)} health ${q(repo.local_path)} --json ${pythonFlag}`)
          .then(out => ({ name: repo.name, data: JSON.parse(out) }))
          .catch(err => ({ name: repo.name, error: err.message }));
      }),
    ]);

    const healthMap = {};
    for (const r of healthArr) healthMap[r.name] = { ...r, pythonInfo: repoPythonInfo[r.name] };

    const html = this._buildDashboard(roles, healthMap, metaMap, codeRepos, condaEnvs, traceMap, artifactCheck);
    this._cachedHtml = html;
    if (this._view) this._view.webview.html = html;
  }

  // ── Traceability parsing ──────────────────────────────────────────────────────

  _parseTraceabilityMatrix(primaryRepoPath) {
    const matrixPath = path.join(primaryRepoPath, 'docs', 'traceability_matrix.md');
    if (!fs.existsSync(matrixPath)) return { found: false };

    const text = fs.readFileSync(matrixPath, 'utf8');

    const covMatch = text.match(/\*\*Coverage:\*\*\s*([\d.]+)%\s*\((\d+)\s*\/\s*(\d+)/);
    const coveragePct  = covMatch ? parseFloat(covMatch[1]) : null;
    const coveredCount = covMatch ? parseInt(covMatch[2]) : null;
    const totalCount   = covMatch ? parseInt(covMatch[3]) : null;

    const gradeMatch = text.match(/\*\*Overall Score:\*\*\s*([\d.]+)%.*\*\*Grade:\*\*\s*([A-F])/);
    const forgeScore = gradeMatch ? parseFloat(gradeMatch[1]) : null;
    const forgeGrade = gradeMatch ? gradeMatch[2] : null;

    const statusCounts = { PASS: 0, LINKED: 0, FAIL: 0, UNTESTED: 0 };
    const rows = text.split('\n').filter(l => /^\|\s*[A-Z]+-\d+/.test(l));
    for (const row of rows) {
      const cells = row.split('|').slice(1, -1).map(c => c.trim());
      if (cells.length >= 5) {
        const s = cells[4].trim();
        if (s in statusCounts) statusCounts[s]++;
      }
    }

    return { found: true, coveragePct, coveredCount, totalCount, forgeScore, forgeGrade, statusCounts };
  }

  // ── Required artifact checks ──────────────────────────────────────────────────

  _checkRequiredArtifacts(primaryRepoPath) {
    const checks = [
      { key: 'requirements_yaml',    label: 'docs/requirements.yaml',       path: path.join(primaryRepoPath, 'docs', 'requirements.yaml') },
      { key: 'soup_yaml',            label: 'docs/soup.yaml',               path: path.join(primaryRepoPath, 'docs', 'soup.yaml') },
      { key: 'anomaly_log',          label: 'docs/anomaly-log.yaml',        path: path.join(primaryRepoPath, 'docs', 'anomaly-log.yaml') },
      { key: 'traceability_matrix',  label: 'docs/traceability_matrix.md',  path: path.join(primaryRepoPath, 'docs', 'traceability_matrix.md') },
    ];

    const results = checks.map(c => ({ ...c, present: fs.existsSync(c.path) }));

    // Evidence runs: directory exists and is non-empty
    const evidenceDir = path.join(primaryRepoPath, 'artifacts', 'evidence_runs');
    const evidencePresent = fs.existsSync(evidenceDir) &&
      fs.readdirSync(evidenceDir).some(f => !f.startsWith('.'));
    results.push({
      key: 'evidence_runs', label: 'artifacts/evidence_runs/ (non-empty)',
      path: evidenceDir, present: evidencePresent,
    });

    // RSK requirement: scan requirements.yaml for at least one RSK- id
    const reqYamlPath = path.join(primaryRepoPath, 'docs', 'requirements.yaml');
    const hasRsk = this._parseRskRequirements(reqYamlPath);
    results.push({
      key: 'rsk_requirement', label: 'RSK-NNN requirement in requirements.yaml',
      path: reqYamlPath, present: hasRsk,
    });

    return results;
  }

  _parseRskRequirements(yamlPath) {
    if (!fs.existsSync(yamlPath)) return false;
    try {
      const text = fs.readFileSync(yamlPath, 'utf8');
      return /id:\s*RSK-\d+/.test(text);
    } catch { return false; }
  }

  // ── DHF generation ───────────────────────────────────────────────────────────

  generateDhf() {
    const roles = this._resolveRepos();
    if (!roles) {
      vscode.window.showErrorMessage('No workspace folders open.');
      return;
    }
    const docsRepos = roles.docs;
    if (!docsRepos.length) {
      vscode.window.showErrorMessage('No docs repo detected in this workspace.');
      return;
    }
    if (docsRepos.length === 1) {
      this._runGenerateDhf(docsRepos[0].local_path, docsRepos[0].name, roles.primary);
    } else {
      vscode.window.showQuickPick(docsRepos.map(r => r.name)).then(name => {
        if (!name) return;
        const repo = docsRepos.find(r => r.name === name);
        this._runGenerateDhf(repo.local_path, repo.name, roles.primary);
      });
    }
  }

  _runGenerateDhf(docsRepoPath, docsRepoName, primary) {
    if (!this._dhfChannel) {
      this._dhfChannel = vscode.window.createOutputChannel('Regulatory — DHF');
    }
    const channel = this._dhfChannel;
    channel.clear();
    channel.show(true);
    channel.appendLine(`Generating DHF documents for ${docsRepoName}…`);

    const { python } = resolveProjectPython(primary?.name ?? '', primary?.local_path ?? '');
    const pythonExe = python || 'python3';
    const args = ['-m', 'regulatory_tools.dhf', docsRepoPath];
    if (primary?.local_path) args.push('--base-dir', primary.local_path);

    const { spawn } = require('child_process');
    const proc = spawn(pythonExe, args);
    let stdout = '';

    proc.stdout.on('data', d => { stdout += d.toString(); });
    proc.stderr.on('data', d => { channel.append(d.toString()); });

    proc.on('close', code => {
      if (code === 0) {
        try {
          const report = JSON.parse(stdout);
          channel.appendLine(`Files modified (${report.files_modified.length}):`);
          for (const f of report.files_modified) channel.appendLine(`  • ${f}`);
          if (report.unfilled_vars.length) {
            channel.appendLine(`Unfilled placeholders (${report.unfilled_vars.length}):`);
            for (const [f, v] of report.unfilled_vars) channel.appendLine(`  • ${v}  in  ${f}`);
          }
          channel.appendLine('Done.');
          this.refresh();
        } catch (err) {
          channel.appendLine(stdout);
          channel.appendLine(`Parse error: ${err.message}`);
        }
      } else {
        channel.appendLine(`Process exited with code ${code}.`);
        vscode.window.showErrorMessage(
          `DHF generation failed (exit ${code}). See "Regulatory — DHF" output.`
        );
      }
    });
  }

  // ── No-primary-repo banner ────────────────────────────────────────────────────

  _noPrimaryBanner(codeRepoNames) {
    const list = codeRepoNames.map(n => `<li><code>${escHtml(n)}</code></li>`).join('');
    return `<div class="reg-banner reg-banner-warn">
      <strong>Primary repo not configured.</strong>
      Multiple code repos detected — set <code>regulatory.primaryRepo</code> in VS Code settings
      to one of:<ul>${list}</ul>
    </div>`;
  }

  // ── Dashboard assembly ────────────────────────────────────────────────────────

  _buildDashboard(roles, healthMap, metaMap, codeRepos, condaEnvs, traceMap, artifactCheck) {
    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const needsPrimaryBanner = !roles.primary && roles.supporting.length > 0;

    const body = `
      <div class="toolbar">
        <span class="ts">Updated ${now}</span>
        <span class="cfg">Regulatory Dashboard</span>
      </div>

      <div id="reg-ctx-menu" class="reg-ctx-menu" style="display:none">
        <div class="reg-ctx-item" id="reg-ctx-set-primary"></div>
        <div class="reg-ctx-item" id="reg-ctx-generate-dhf">Generate DHF</div>
      </div>

      ${needsPrimaryBanner ? this._noPrimaryBanner(roles.supporting.map(r => r.name)) : ''}

      <section>
        <div class="section-title">Project Overview</div>
        ${this._buildProjectOverview(roles, healthMap, traceMap)}
      </section>

      ${codeRepos.length ? `<section>
        <div class="section-title">Repository Overview</div>
        <div class="tscroll">${this._buildRepoOverview(metaMap, healthMap, codeRepos)}</div>
      </section>` : ''}

      ${codeRepos.length ? `<section>
        <div class="section-title">Health Details</div>
        ${codeRepos.map(r => this._healthCard(r.name, healthMap[r.name], condaEnvs)).join('')}
      </section>` : ''}

      ${artifactCheck ? `<section>
        <div class="section-title">Required Artifacts</div>
        ${this._buildArtifactSection(artifactCheck)}
      </section>` : ''}
    `;

    return wrapHtml(body + REG_STYLES + REG_SCRIPTS);
  }

  // ── Section builders ──────────────────────────────────────────────────────────

  _buildProjectOverview(roles, healthMap, traceMap) {
    const allRepos = roles.all;
    const rows = allRepos.map(repo => {
      const isPrimary   = repo === roles.primary;
      const isSupporting = roles.supporting.includes(repo);
      const isDocs      = roles.docs.includes(repo);

      const roleLabel = isPrimary ? 'primary' : isSupporting ? 'supporting' : isDocs ? 'docs' : '—';
      const roleCls   = isPrimary ? 'role-primary' : isSupporting ? 'role-supporting' : isDocs ? 'role-docs' : 'role-none';

      const health = healthMap[repo.name];
      const grade  = health?.data?.grade ?? (health?.error ? 'ERR' : '—');
      const col    = { A: '#4EC9B0', B: '#DCDCAA', C: '#CE9178', D: '#F44747', F: '#F44747' }[grade] ?? '#888';
      const gradeBadge = grade !== '—'
        ? `<span class="sum-badge" style="background:${col}">${escHtml(grade)}</span>`
        : '—';

      let covCell = '—', statusCell = '—';
      const repoTrace = (isPrimary || isSupporting) ? (traceMap[repo.name] ?? { found: false }) : { found: false };
      if (repoTrace.found) {
        const pct = repoTrace.coveragePct != null ? `${repoTrace.coveragePct.toFixed(0)}%` : '—';
        const sc = repoTrace.statusCounts;
        covCell = pct;
        statusCell = [
          sc.PASS   ? `<span class="reg-pass">${sc.PASS} PASS</span>`     : '',
          sc.LINKED ? `<span class="reg-linked">${sc.LINKED} LINKED</span>` : '',
          sc.FAIL   ? `<span class="reg-fail">${sc.FAIL} FAIL</span>`     : '',
          sc.UNTESTED ? `<span class="reg-muted">${sc.UNTESTED} UNTESTED</span>` : '',
        ].filter(Boolean).join(' ');
      }

      const repoType = isDocs ? 'docs' : 'code';
      const isPrimaryAttr = isDocs ? '' : ` data-is-primary="${isPrimary}"`;
      return `<tr data-repo-name="${escHtml(repo.name)}" data-repo-type="${repoType}"${isPrimaryAttr}>
        <td class="sum-name">${escHtml(repo.name)}</td>
        <td><span class="reg-role ${roleCls}">${roleLabel}</span></td>
        <td class="sum-grade">${gradeBadge}</td>
        <td class="reg-cov">${covCell}</td>
        <td class="reg-status">${statusCell || '—'}</td>
      </tr>`;
    }).join('');

    return `<table class="sum-table">
      <thead><tr>
        <th>Repo</th><th>Role</th><th>Grade</th><th>Req Cov</th><th>Traceability</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  }

  _buildArtifactSection(checks) {
    const rows = checks.map(c => {
      const icon = c.present ? '<span class="reg-pass">✓</span>' : '<span class="reg-fail">✗</span>';
      return `<tr>
        <td class="reg-art-icon">${icon}</td>
        <td class="reg-art-label"><code>${escHtml(c.label)}</code></td>
      </tr>`;
    }).join('');

    return `<table class="reg-art-table"><tbody>${rows}</tbody></table>`;
  }

  // Delegate to shared.js — changes to shared.js flow here automatically.
  _buildRepoOverview(metaMap, healthMap, codeRepos) {
    return buildRepoOverview(metaMap, healthMap, codeRepos);
  }
  _healthCard(name, result, condaEnvs) {
    return buildHealthCard(name, result, condaEnvs);
  }
}

// ── Regulatory-panel-specific CSS (appended inside wrapHtml body) ─────────────

const REG_STYLES = `<style>
/* Role badges */
.reg-role {
  display: inline-block; font-size: 0.72em; padding: 1px 6px; border-radius: 3px;
  font-weight: 600; white-space: nowrap;
}
.role-primary   { background: rgba(78,201,176,.18);  color: #4EC9B0; }
.role-supporting{ background: rgba(100,100,100,.2);  color: #aaa; }
.role-docs      { background: rgba(220,220,170,.12); color: #DCDCAA; }
.role-none      { color: #555; }

/* Coverage + traceability cells */
.reg-cov    { text-align: right; font-variant-numeric: tabular-nums; width: 52px; }
.reg-status { font-size: 0.78em; white-space: nowrap; }
.reg-pass   { color: #4EC9B0; font-weight: 600; }
.reg-fail   { color: #F44747; font-weight: 600; }
.reg-linked { color: #DCDCAA; }
.reg-muted  { color: #666; }

/* Banner */
.reg-banner {
  border-radius: 4px; padding: 8px 10px; margin-bottom: 10px; font-size: 0.82em;
}
.reg-banner-warn {
  background: rgba(220,220,170,.12); border-left: 3px solid #DCDCAA;
}
.reg-banner-warn strong { color: #DCDCAA; }
.reg-banner ul { margin: 4px 0 0 16px; }

/* Artifact check table */
.reg-art-table { border-collapse: collapse; width: 100%; font-size: 0.82em; }
.reg-art-table td { padding: 3px 4px; }
.reg-art-icon  { width: 20px; text-align: center; }
.reg-art-label { font-family: monospace; }

/* Context menu */
.reg-ctx-menu {
  position: fixed; z-index: 100;
  background: var(--vscode-menu-background, #252526);
  border: 1px solid var(--vscode-menu-border, #454545);
  border-radius: 4px; padding: 2px 0; min-width: 130px;
  box-shadow: 0 2px 8px rgba(0,0,0,.4);
}
.reg-ctx-item {
  padding: 5px 12px; cursor: pointer; font-size: 0.82em;
  color: var(--vscode-menu-foreground, #ccc);
}
.reg-ctx-item:hover {
  background: var(--vscode-menu-selectionBackground, #094771);
  color: var(--vscode-menu-selectionForeground, #fff);
}
</style>`;

const REG_SCRIPTS = `<script>(function () {
  const vscode = acquireVsCodeApi();
  let activeRepo = null;

  const menu = document.getElementById('reg-ctx-menu');
  const itemSetPrimary  = document.getElementById('reg-ctx-set-primary');
  const itemGenerateDhf = document.getElementById('reg-ctx-generate-dhf');

  document.addEventListener('contextmenu', e => {
    if (menu) menu.style.display = 'none';
    const tr = e.target.closest('tr[data-repo-type="code"], tr[data-repo-type="docs"]');
    if (!tr || !menu) return;
    e.preventDefault();
    const repoType = tr.dataset.repoType;
    activeRepo = { name: tr.dataset.repoName, type: repoType, isPrimary: tr.dataset.isPrimary === 'true' };
    if (itemSetPrimary) {
      itemSetPrimary.style.display = repoType === 'code' ? '' : 'none';
      if (repoType === 'code') {
        itemSetPrimary.textContent = activeRepo.isPrimary ? 'Unset Primary' : 'Set as Primary';
      }
    }
    if (itemGenerateDhf) itemGenerateDhf.style.display = repoType === 'docs' ? '' : 'none';
    menu.style.left = e.clientX + 'px';
    menu.style.top  = e.clientY + 'px';
    menu.style.display = 'block';
  });

  document.addEventListener('click', () => {
    if (menu) menu.style.display = 'none';
  });

  itemSetPrimary?.addEventListener('click', () => {
    if (!activeRepo) return;
    vscode.postMessage({
      command: 'setPrimaryRepo',
      name: activeRepo.isPrimary ? '' : activeRepo.name,
    });
    activeRepo = null;
  });

  itemGenerateDhf?.addEventListener('click', () => {
    if (!activeRepo) return;
    vscode.postMessage({ command: 'generateDhf', docsRepoName: activeRepo.name });
    activeRepo = null;
  });
})();</script>`;

module.exports = { RegulatoryWebviewProvider };
