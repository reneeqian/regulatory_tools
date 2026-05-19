'use strict';
// Tests for regulatory-tools-vscode-panel/src/provider.js
// REG-001 through REG-008

const Module = require('module');
const _origLoad = Module._load;
// Single cached instance so provider.js and fakeVscode() share the same object.
const vscodeMock = {
  workspace: {
    getConfiguration: () => ({ get: () => '' }),
    workspaceFolders: [],
  },
  env: {},
  ConfigurationTarget: { Global: 1 },
};
Module._load = function (request, ...args) {
  if (request === 'vscode') return vscodeMock;
  return _origLoad.call(this, request, ...args);
};

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');

const { RegulatoryWebviewProvider } = require('../src/provider');

const p = new RegulatoryWebviewProvider({ fsPath: '/fake/ext' });

let passed = 0, failed = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`  ✓ ${name}`);
    passed++;
  } catch (e) {
    console.error(`  ✗ ${name}\n    ${e.message}`);
    failed++;
  }
}

// ── shared.js import (REG-005) ────────────────────────────────────────────────

console.log('\nshared.js import (REG-005)');

test('shared.js loads via relative path', () => {
  const SHARED = path.join(__dirname, '../../../forge/forge-vscode-panel/src/shared.js');
  assert.ok(fs.existsSync(SHARED), `shared.js not found at: ${SHARED}`);
  const shared = require(SHARED);
  assert.strictEqual(typeof shared.buildRepoOverview, 'function');
  assert.strictEqual(typeof shared.buildHealthCard, 'function');
  assert.strictEqual(typeof shared.wrapHtml, 'function');
});

test('_buildRepoOverview delegates to shared buildRepoOverview', () => {
  const SHARED = path.join(__dirname, '../../../forge/forge-vscode-panel/src/shared.js');
  const { buildRepoOverview } = require(SHARED);
  const metaMap  = { r: { branch: 'dev', ahead: 0, behind: 0, prNumber: null, prUrl: null, ciPassed: null, ciTotal: null } };
  const healthMap = { r: { data: { grade: 'A', overall_score: 0.95 } } };
  const repos    = [{ name: 'r', local_path: '/fake/r' }];
  const fromProvider = p._buildRepoOverview(metaMap, healthMap, repos);
  const fromShared   = buildRepoOverview(metaMap, healthMap, repos);
  assert.strictEqual(fromProvider, fromShared);
});

// ── _detectRepoType (REG-002) ─────────────────────────────────────────────────

console.log('\n_detectRepoType (REG-002)');

function withTmpDir(fn) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'reg-test-'));
  try { fn(tmp); } finally { fs.rmSync(tmp, { recursive: true, force: true }); }
}

test('classifies dir with pyproject.toml as code', () => {
  withTmpDir(tmp => {
    fs.writeFileSync(path.join(tmp, 'pyproject.toml'), '');
    assert.strictEqual(p._detectRepoType(tmp), 'code');
  });
});

test('classifies dir with package.json as code', () => {
  withTmpDir(tmp => {
    fs.writeFileSync(path.join(tmp, 'package.json'), '');
    assert.strictEqual(p._detectRepoType(tmp), 'code');
  });
});

test('classifies dir with setup.py as code', () => {
  withTmpDir(tmp => {
    fs.writeFileSync(path.join(tmp, 'setup.py'), '');
    assert.strictEqual(p._detectRepoType(tmp), 'code');
  });
});

test('classifies dir with .py file in src/ as code', () => {
  withTmpDir(tmp => {
    fs.mkdirSync(path.join(tmp, 'src'));
    fs.writeFileSync(path.join(tmp, 'src', 'main.py'), '');
    assert.strictEqual(p._detectRepoType(tmp), 'code');
  });
});

test('classifies markdown-only dir as docs', () => {
  withTmpDir(tmp => {
    fs.writeFileSync(path.join(tmp, 'README.md'), '');
    fs.writeFileSync(path.join(tmp, 'design.md'), '');
    assert.strictEqual(p._detectRepoType(tmp), 'docs');
  });
});

test('classifies empty dir as docs', () => {
  withTmpDir(tmp => {
    assert.strictEqual(p._detectRepoType(tmp), 'docs');
  });
});

// ── _resolveRepos (REG-001, REG-003) ─────────────────────────────────────────

console.log('\n_resolveRepos (REG-001, REG-003)');

function fakeVscode(folders, primarySetting = '') {
  const origFolders = vscodeMock.workspace.workspaceFolders;
  const origGetCfg  = vscodeMock.workspace.getConfiguration;
  vscodeMock.workspace.workspaceFolders = folders;
  vscodeMock.workspace.getConfiguration = () => ({ get: (key) => key === 'primaryRepo' ? primarySetting : '' });
  return () => {
    vscodeMock.workspace.workspaceFolders = origFolders;
    vscodeMock.workspace.getConfiguration = origGetCfg;
  };
}

test('returns null when no workspace folders are open', () => {
  const restore = fakeVscode([]);
  try {
    const result = p._resolveRepos();
    assert.strictEqual(result, null);
  } finally { restore(); }
});

test('auto-selects primary when only one code repo detected', () => {
  withTmpDir(tmp => {
    fs.writeFileSync(path.join(tmp, 'pyproject.toml'), '');
    const restore = fakeVscode([{ name: 'myproject', uri: { fsPath: tmp } }]);
    try {
      const roles = p._resolveRepos();
      assert.ok(roles.primary, 'primary should be set');
      assert.strictEqual(roles.primary.name, 'myproject');
      assert.strictEqual(roles.supporting.length, 0);
    } finally { restore(); }
  });
});

test('primary is null and supporting has both when multiple code repos and no setting', () => {
  withTmpDir(tmp1 => {
    withTmpDir(tmp2 => {
      fs.writeFileSync(path.join(tmp1, 'pyproject.toml'), '');
      fs.writeFileSync(path.join(tmp2, 'pyproject.toml'), '');
      const restore = fakeVscode([
        { name: 'repo_a', uri: { fsPath: tmp1 } },
        { name: 'repo_b', uri: { fsPath: tmp2 } },
      ]);
      try {
        const roles = p._resolveRepos();
        assert.strictEqual(roles.primary, null);
        assert.strictEqual(roles.supporting.length, 2);
      } finally { restore(); }
    });
  });
});

test('uses regulatory.primaryRepo setting when set', () => {
  withTmpDir(tmp1 => {
    withTmpDir(tmp2 => {
      fs.writeFileSync(path.join(tmp1, 'pyproject.toml'), '');
      fs.writeFileSync(path.join(tmp2, 'pyproject.toml'), '');
      const restore = fakeVscode(
        [
          { name: 'repo_a', uri: { fsPath: tmp1 } },
          { name: 'repo_b', uri: { fsPath: tmp2 } },
        ],
        'repo_b'
      );
      try {
        const roles = p._resolveRepos();
        assert.ok(roles.primary, 'primary should be set');
        assert.strictEqual(roles.primary.name, 'repo_b');
        assert.strictEqual(roles.supporting.length, 1);
        assert.strictEqual(roles.supporting[0].name, 'repo_a');
      } finally { restore(); }
    });
  });
});

test('docs repos are classified separately', () => {
  withTmpDir(code => {
    withTmpDir(docs => {
      fs.writeFileSync(path.join(code, 'pyproject.toml'), '');
      // docs dir has only .md files → classified as docs
      fs.writeFileSync(path.join(docs, 'README.md'), '');
      const restore = fakeVscode([
        { name: 'myproject', uri: { fsPath: code } },
        { name: 'SaMD-DHF-Templates', uri: { fsPath: docs } },
      ]);
      try {
        const roles = p._resolveRepos();
        assert.strictEqual(roles.primary.name, 'myproject');
        assert.strictEqual(roles.docs.length, 1);
        assert.strictEqual(roles.docs[0].name, 'SaMD-DHF-Templates');
      } finally { restore(); }
    });
  });
});

// ── _parseTraceabilityMatrix (REG-006) ────────────────────────────────────────

console.log('\n_parseTraceabilityMatrix (REG-006)');

const FIXTURE_MATRIX = `<!-- AUTO-GENERATED FILE. DO NOT EDIT MANUALLY. -->

# Requirements Traceability Matrix

## Requirement Coverage

**Coverage:** 100.0% (19 / 19 requirements tested)

## Forge Code Health

**Overall Score:** 91.5%  **Grade:** A

| Requirement ID | Title | Linked Tests | Evidence Artifacts | Status |
|----------------|-------|--------------|--------------------|--------|
| DOC-001 | Machine-Readable Requirements | tests/test_x.py::test_a |  | LINKED |
| INF-001 | Artifact Collection Support | tests/test_x.py::test_b |  | LINKED |
| RSK-001 | Evidence Classification | tests/test_x.py::test_c | artifact.json | PASS |
| VER-001 | Requirement Validation | tests/test_x.py::test_d |  | FAIL |
| SYS-001 | CI-Compatible Execution | tests/test_x.py::test_e |  | UNTESTED |
`;

test('parses coverage percentage correctly', () => {
  withTmpDir(tmp => {
    const docsDir = path.join(tmp, 'docs');
    fs.mkdirSync(docsDir);
    fs.writeFileSync(path.join(docsDir, 'traceability_matrix.md'), FIXTURE_MATRIX);
    const result = p._parseTraceabilityMatrix(tmp);
    assert.ok(result.found, 'should find the matrix');
    assert.strictEqual(result.coveragePct, 100.0);
    assert.strictEqual(result.coveredCount, 19);
    assert.strictEqual(result.totalCount, 19);
  });
});

test('parses forge grade correctly', () => {
  withTmpDir(tmp => {
    const docsDir = path.join(tmp, 'docs');
    fs.mkdirSync(docsDir);
    fs.writeFileSync(path.join(docsDir, 'traceability_matrix.md'), FIXTURE_MATRIX);
    const result = p._parseTraceabilityMatrix(tmp);
    assert.strictEqual(result.forgeGrade, 'A');
    assert.strictEqual(result.forgeScore, 91.5);
  });
});

test('counts PASS/LINKED/FAIL/UNTESTED correctly', () => {
  withTmpDir(tmp => {
    const docsDir = path.join(tmp, 'docs');
    fs.mkdirSync(docsDir);
    fs.writeFileSync(path.join(docsDir, 'traceability_matrix.md'), FIXTURE_MATRIX);
    const result = p._parseTraceabilityMatrix(tmp);
    assert.strictEqual(result.statusCounts.PASS, 1);
    assert.strictEqual(result.statusCounts.LINKED, 2);
    assert.strictEqual(result.statusCounts.FAIL, 1);
    assert.strictEqual(result.statusCounts.UNTESTED, 1);
  });
});

test('returns found:false when matrix file is absent', () => {
  withTmpDir(tmp => {
    const result = p._parseTraceabilityMatrix(tmp);
    assert.strictEqual(result.found, false);
  });
});

// ── _parseRskRequirements (REG-008) ───────────────────────────────────────────

console.log('\n_parseRskRequirements (REG-008)');

test('returns true when RSK-NNN requirement is present', () => {
  withTmpDir(tmp => {
    const yamlPath = path.join(tmp, 'requirements.yaml');
    fs.writeFileSync(yamlPath, 'requirements:\n  - id: RSK-001\n    title: Risk Control\n');
    assert.strictEqual(p._parseRskRequirements(yamlPath), true);
  });
});

test('returns false when no RSK requirement exists', () => {
  withTmpDir(tmp => {
    const yamlPath = path.join(tmp, 'requirements.yaml');
    fs.writeFileSync(yamlPath, 'requirements:\n  - id: SYS-001\n    title: System Req\n');
    assert.strictEqual(p._parseRskRequirements(yamlPath), false);
  });
});

test('returns false when file does not exist', () => {
  assert.strictEqual(p._parseRskRequirements('/nonexistent/requirements.yaml'), false);
});

// ── _checkRequiredArtifacts (REG-007) ─────────────────────────────────────────

console.log('\n_checkRequiredArtifacts (REG-007)');

test('marks requirements.yaml as present when file exists', () => {
  withTmpDir(tmp => {
    const docsDir = path.join(tmp, 'docs');
    fs.mkdirSync(docsDir);
    fs.writeFileSync(path.join(docsDir, 'requirements.yaml'), '');
    const checks = p._checkRequiredArtifacts(tmp);
    const req = checks.find(c => c.key === 'requirements_yaml');
    assert.ok(req.present, 'requirements.yaml should be present');
  });
});

test('marks soup.yaml as missing when absent', () => {
  withTmpDir(tmp => {
    fs.mkdirSync(path.join(tmp, 'docs'));
    const checks = p._checkRequiredArtifacts(tmp);
    const soup = checks.find(c => c.key === 'soup_yaml');
    assert.strictEqual(soup.present, false);
  });
});

test('marks anomaly-log.yaml as missing when absent', () => {
  withTmpDir(tmp => {
    fs.mkdirSync(path.join(tmp, 'docs'));
    const checks = p._checkRequiredArtifacts(tmp);
    const anomaly = checks.find(c => c.key === 'anomaly_log');
    assert.strictEqual(anomaly.present, false);
  });
});

test('marks evidence_runs as present when directory has files', () => {
  withTmpDir(tmp => {
    const evidenceDir = path.join(tmp, 'artifacts', 'evidence_runs');
    fs.mkdirSync(evidenceDir, { recursive: true });
    fs.writeFileSync(path.join(evidenceDir, 'test_result.json'), '{}');
    const checks = p._checkRequiredArtifacts(tmp);
    const ev = checks.find(c => c.key === 'evidence_runs');
    assert.ok(ev.present, 'evidence_runs should be present');
  });
});

test('marks evidence_runs as missing when directory is empty', () => {
  withTmpDir(tmp => {
    const evidenceDir = path.join(tmp, 'artifacts', 'evidence_runs');
    fs.mkdirSync(evidenceDir, { recursive: true });
    const checks = p._checkRequiredArtifacts(tmp);
    const ev = checks.find(c => c.key === 'evidence_runs');
    assert.strictEqual(ev.present, false);
  });
});

test('marks rsk_requirement present when RSK id exists in requirements.yaml', () => {
  withTmpDir(tmp => {
    const docsDir = path.join(tmp, 'docs');
    fs.mkdirSync(docsDir);
    fs.writeFileSync(path.join(docsDir, 'requirements.yaml'), '  - id: RSK-001\n');
    const checks = p._checkRequiredArtifacts(tmp);
    const rsk = checks.find(c => c.key === 'rsk_requirement');
    assert.ok(rsk.present, 'RSK requirement should be present');
  });
});

// ── _buildProjectOverview HTML (REG-004) ──────────────────────────────────────

console.log('\n_buildProjectOverview HTML (REG-004)');

function makeRoles(primaryName, supportingNames = [], docsNames = []) {
  const makeRepo = n => ({ name: n, local_path: `/fake/${n}`, repoType: 'code' });
  const primary = primaryName ? makeRepo(primaryName) : null;
  const supporting = supportingNames.map(makeRepo);
  const docs = docsNames.map(n => ({ name: n, local_path: `/fake/${n}`, repoType: 'docs' }));
  return { primary, supporting, docs, all: [...(primary ? [primary] : []), ...supporting, ...docs] };
}

test('renders primary role badge', () => {
  const roles = makeRoles('myproject');
  const html = p._buildProjectOverview(roles, {}, { found: false });
  assert.ok(html.includes('role-primary'), 'should have primary role class');
  assert.ok(html.includes('primary'), 'should show "primary" label');
});

test('renders supporting role badge', () => {
  const roles = makeRoles('main', ['tool']);
  const html = p._buildProjectOverview(roles, {}, { found: false });
  assert.ok(html.includes('role-supporting'));
});

test('renders docs role badge', () => {
  const roles = makeRoles('main', [], ['DHF']);
  const html = p._buildProjectOverview(roles, {}, { found: false });
  assert.ok(html.includes('role-docs'));
});

test('shows grade badge when health data present', () => {
  const roles = makeRoles('myproject');
  const healthMap = { myproject: { data: { grade: 'B', overall_score: 0.82 } } };
  const html = p._buildProjectOverview(roles, healthMap, { found: false });
  assert.ok(html.includes('>B<'), 'grade badge should contain B');
});

test('shows coverage % from traceability data', () => {
  const roles = makeRoles('myproject');
  const traceData = { found: true, coveragePct: 94.7, coveredCount: 18, totalCount: 19,
                      forgeGrade: 'A', forgeScore: 91.5,
                      statusCounts: { PASS: 10, LINKED: 8, FAIL: 0, UNTESTED: 1 } };
  const html = p._buildProjectOverview(roles, {}, traceData);
  assert.ok(html.includes('95%'), 'should show rounded coverage percentage');
  assert.ok(html.includes('10 PASS'), 'should show PASS count');
  assert.ok(html.includes('8 LINKED'), 'should show LINKED count');
});

// ── _buildArtifactSection HTML (REG-007) ──────────────────────────────────────

console.log('\n_buildArtifactSection HTML (REG-007)');

test('renders ✓ for present artifacts', () => {
  const checks = [{ key: 'x', label: 'docs/requirements.yaml', path: '/fake', present: true }];
  const html = p._buildArtifactSection(checks);
  assert.ok(html.includes('✓'), 'should show check mark');
  assert.ok(html.includes('reg-pass'), 'should use pass class');
});

test('renders ✗ for missing artifacts', () => {
  const checks = [{ key: 'x', label: 'docs/anomaly-log.yaml', path: '/fake', present: false }];
  const html = p._buildArtifactSection(checks);
  assert.ok(html.includes('✗'), 'should show cross mark');
  assert.ok(html.includes('reg-fail'), 'should use fail class');
});

test('renders artifact label', () => {
  const checks = [{ key: 'x', label: 'docs/soup.yaml', path: '/fake', present: true }];
  const html = p._buildArtifactSection(checks);
  assert.ok(html.includes('docs/soup.yaml'), 'should include label text');
});

// ── Summary ───────────────────────────────────────────────────────────────────

console.log(`\n${passed + failed} tests: ${passed} passed, ${failed} failed\n`);
if (failed) process.exit(1);
