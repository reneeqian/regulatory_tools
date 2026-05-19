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

    // Synchronous artifact checks (no subprocess) run immediately.
    const traceData = primaryPath ? this._parseTraceabilityMatrix(primaryPath) : { found: false };
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

    const html = this._buildDashboard(roles, healthMap, metaMap, codeRepos, condaEnvs, traceData, artifactCheck);
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

  _buildDashboard(roles, healthMap, metaMap, codeRepos, condaEnvs, traceData, artifactCheck) {
    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const needsPrimaryBanner = !roles.primary && roles.supporting.length > 0;

    const body = `
      <div class="toolbar">
        <span class="ts">Updated ${now}</span>
        <span class="cfg">Regulatory Dashboard</span>
      </div>

      ${needsPrimaryBanner ? this._noPrimaryBanner(roles.supporting.map(r => r.name)) : ''}

      <section>
        <div class="section-title">Project Overview</div>
        ${this._buildProjectOverview(roles, healthMap, traceData)}
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

    return wrapHtml(body + REG_STYLES);
  }

  // ── Section builders ──────────────────────────────────────────────────────────

  _buildProjectOverview(roles, healthMap, traceData) {
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
      if (isPrimary && traceData.found) {
        const pct = traceData.coveragePct != null ? `${traceData.coveragePct.toFixed(0)}%` : '—';
        const sc = traceData.statusCounts;
        covCell = pct;
        statusCell = [
          sc.PASS   ? `<span class="reg-pass">${sc.PASS} PASS</span>`     : '',
          sc.LINKED ? `<span class="reg-linked">${sc.LINKED} LINKED</span>` : '',
          sc.FAIL   ? `<span class="reg-fail">${sc.FAIL} FAIL</span>`     : '',
          sc.UNTESTED ? `<span class="reg-muted">${sc.UNTESTED} UNTESTED</span>` : '',
        ].filter(Boolean).join(' ');
      }

      return `<tr>
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
</style>`;

module.exports = { RegulatoryWebviewProvider };
