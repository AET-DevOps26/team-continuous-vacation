#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";

const artifactRoot = process.env.COVERAGE_ARTIFACT_ROOT || ".coverage-artifacts";
const outputDir = ".sonar/coverage";

fs.mkdirSync(outputDir, { recursive: true });

copyJacoco("backend-coverage/jacocoTestReport.xml", "backend-jacoco.xml");
copyJacoco("persistence-service-coverage/jacocoTestReport.xml", "persistence-service-jacoco.xml");
rewriteLcov(
  path.join(artifactRoot, "frontend-coverage/lcov.info"),
  path.join(outputDir, "frontend.lcov"),
  "frontend/",
);
rewriteCoveragePy(
  path.join(artifactRoot, "genai-service-coverage/coverage.xml"),
  path.join(outputDir, "genai-service-coverage.xml"),
  "genai-service/",
);
rewriteCoveragePy(
  path.join(artifactRoot, "travel-context-service-coverage/coverage.xml"),
  path.join(outputDir, "travel-context-service-coverage.xml"),
  "travel-context-service/",
);

function copyJacoco(input, output) {
  const source = path.join(artifactRoot, input);
  if (fs.existsSync(source)) {
    fs.copyFileSync(source, path.join(outputDir, output));
  }
}

function rewriteLcov(input, output, prefix) {
  if (!fs.existsSync(input)) {
    return;
  }

  const rewritten = fs
    .readFileSync(input, "utf8")
    .replace(/^SF:src\//gm, `SF:${prefix}src/`);

  fs.writeFileSync(output, rewritten);
}

function rewriteCoveragePy(input, output, prefix) {
  if (!fs.existsSync(input)) {
    return;
  }

  const rewritten = fs
    .readFileSync(input, "utf8")
    .replace(/<source>.*?<\/source>/gs, "<source>.</source>")
    .replace(/filename="app\//g, `filename="${prefix}app/`);

  fs.writeFileSync(output, rewritten);
}
