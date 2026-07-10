#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";

const threshold = Number(process.env.COVERAGE_THRESHOLD || "80");
const artifactRoot = process.env.COVERAGE_ARTIFACT_ROOT || ".coverage-artifacts";
const summaryPath = process.env.COVERAGE_SUMMARY_PATH || "coverage-summary.md";
const checkOnly = process.argv.includes("--check");

const services = [
  {
    name: "Frontend",
    job: "build-frontend",
    report: "frontend-coverage/lcov.info",
    parser: parseLcov,
  },
  {
    name: "Backend",
    job: "build-backend",
    report: "backend-coverage/jacocoTestReport.xml",
    parser: parseJacoco,
  },
  {
    name: "Persistence service",
    job: "build-persistence-service",
    report: "persistence-service-coverage/jacocoTestReport.xml",
    parser: parseJacoco,
  },
  {
    name: "GenAI service",
    job: "build-genai",
    report: "genai-service-coverage/coverage.xml",
    parser: parseCoveragePy,
  },
  {
    name: "Travel context service",
    job: "build-travel-context",
    report: "travel-context-service-coverage/coverage.xml",
    parser: parseCoveragePy,
  },
];

const needs = parseNeeds(process.env.NEEDS_JSON);
const results = services.map((service) => readCoverage(service, needs));
const failing = results.filter((result) => !result.ok);

if (!checkOnly) {
  const markdown = renderMarkdown(results, threshold);
  fs.writeFileSync(summaryPath, markdown);

  if (process.env.GITHUB_STEP_SUMMARY) {
    fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, `${markdown}\n`);
  }
}

if (failing.length > 0 && checkOnly) {
  console.error(`Coverage gate failed: ${formatFailures(failing)}`);
  process.exit(1);
}

if (failing.length > 0) {
  console.warn(`Coverage gate would fail: ${formatFailures(failing)}`);
}

function readCoverage(service, needsByJob) {
  const jobResult = needsByJob?.[service.job]?.result;
  const reportPath = path.join(artifactRoot, service.report);

  if (!fs.existsSync(reportPath)) {
    const missingReason =
      jobResult && jobResult !== "success"
        ? `job ${jobResult}; coverage report missing`
        : "coverage report missing";

    return {
      ...service,
      ok: false,
      reason: missingReason,
      covered: 0,
      total: 0,
      percent: 0,
    };
  }

  try {
    const coverage = service.parser(fs.readFileSync(reportPath, "utf8"));
    const percent = coverage.total === 0 ? 0 : (coverage.covered / coverage.total) * 100;

    const coverageOk = percent >= threshold;
    const jobOk = !jobResult || jobResult === "success";

    return {
      ...service,
      ...coverage,
      percent,
      ok: coverageOk && jobOk,
      reason: [coverageOk ? "ok" : `below ${threshold}%`, jobOk ? undefined : `job ${jobResult}`]
        .filter(Boolean)
        .join("; "),
    };
  } catch (error) {
    return {
      ...service,
      ok: false,
      reason: error.message,
      covered: 0,
      total: 0,
      percent: 0,
    };
  }
}

function parseLcov(content) {
  let covered = 0;
  let total = 0;

  for (const line of content.split(/\r?\n/)) {
    if (line.startsWith("LH:")) {
      covered += Number(line.slice(3));
    } else if (line.startsWith("LF:")) {
      total += Number(line.slice(3));
    }
  }

  if (total === 0) {
    throw new Error("no line counters found");
  }

  return { covered, total };
}

function parseJacoco(content) {
  const counters = [...content.matchAll(/<counter\s+type="LINE"\s+missed="(\d+)"\s+covered="(\d+)"\/>/g)];
  const totalCounter = counters.at(-1);

  if (!totalCounter) {
    throw new Error("no JaCoCo line counter found");
  }

  const missed = Number(totalCounter[1]);
  const covered = Number(totalCounter[2]);

  return { covered, total: covered + missed };
}

function parseCoveragePy(content) {
  const coveredMatch = content.match(/lines-covered="(\d+)"/);
  const validMatch = content.match(/lines-valid="(\d+)"/);

  if (!coveredMatch || !validMatch) {
    throw new Error("no coverage.py line counters found");
  }

  return {
    covered: Number(coveredMatch[1]),
    total: Number(validMatch[1]),
  };
}

function parseNeeds(rawNeeds) {
  if (!rawNeeds) {
    return undefined;
  }

  try {
    return JSON.parse(rawNeeds);
  } catch {
    return undefined;
  }
}

function renderMarkdown(results, minimum) {
  const rows = results
    .map((result) => {
      const status = result.ok ? "Pass" : "Fail";
      const coverage = result.total === 0 ? "n/a" : `${result.percent.toFixed(2)}%`;
      const lines = result.total === 0 ? "n/a" : `${result.covered}/${result.total}`;
      return `| ${result.name} | ${coverage} | ${lines} | ${status} | ${result.reason} |`;
    })
    .join("\n");

  const overall = results.every((result) => result.ok) ? "Pass" : "Fail";

  return `<!-- triptailor-coverage-report -->
## Coverage report

Minimum required line coverage per service: **${minimum}%**

| Service | Line coverage | Covered lines | Gate | Notes |
| --- | ---: | ---: | --- | --- |
${rows}

Overall gate: **${overall}**
`;
}

function formatFailures(results) {
  return results.map((result) => `${result.name} (${result.reason})`).join(", ");
}
