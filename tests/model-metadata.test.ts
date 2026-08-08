import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

const projectRoot = new URL("../", import.meta.url);
const metadata = JSON.parse(
  await readFile(new URL("data/model-metadata.json", projectRoot), "utf8"),
);
const catalog = JSON.parse(
  await readFile(new URL("data/model-release-catalog.json", projectRoot), "utf8"),
);
const runs = JSON.parse(
  await readFile(new URL("app/data/runs.generated.json", projectRoot), "utf8"),
);

function aliasKey(provider: string, name: string) {
  return `${provider.trim().toLowerCase()}/${name.trim().toLowerCase()}`;
}

test("every indexed model has release metadata", () => {
  const aliases = new Set(
    metadata.models.flatMap((model: { aliases: Array<{ provider: string; name: string }> }) =>
      model.aliases.map((alias) => aliasKey(alias.provider, alias.name)),
    ),
  );

  for (const run of runs) {
    assert.ok(
      aliases.has(aliasKey(run.model.provider, run.model.name)),
      `release metadata is missing for ${run.model.provider}/${run.model.name}`,
    );
  }
});

test("chart metadata is backed by the local release catalog", async () => {
  const releases = new Map(
    [...catalog.models, ...catalog.localAdditions].map((model) => [
      model.name,
      model.releaseDate,
    ]),
  );

  for (const model of metadata.models) {
    assert.equal(
      model.releaseDate,
      releases.get(model.displayName),
      `${model.displayName} should match the saved release catalog`,
    );
    await access(new URL(`public${model.icon}`, projectRoot));
  }
});
