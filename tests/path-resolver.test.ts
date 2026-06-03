import { test } from 'node:test';
import * as assert from 'node:assert';
import * as fs from 'fs';
import * as path from 'path';
import { resolveTopicPath } from '../src/crawler/path-resolver';

const tempDir = path.join(__dirname, 'temp_resolver');

test('Path Resolver Tests', async (t) => {
  if (fs.existsSync(tempDir)) {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
  fs.mkdirSync(tempDir, { recursive: true });

  await t.test('should resolve topic path and create category folder when count is below limit', () => {
    const category = 'gov-agencies';
    const filename = 'NCO';
    
    const resolvedPath = resolveTopicPath(tempDir, category, filename, 100, 95);
    
    // Should resolve to tempDir/topics/gov-agencies/NCO.md
    const expected = path.join(tempDir, 'topics', 'gov-agencies', 'NCO.md');
    assert.strictEqual(resolvedPath, expected);
    assert.ok(fs.existsSync(path.dirname(resolvedPath)));
  });

  await t.test('should fallback to misc directory when category folders are equal/above threshold', () => {
    // Populate tempDir/topics with 95 dummy folders
    const topicsDir = path.join(tempDir, 'topics');
    for (let i = 0; i < 95; i++) {
      fs.mkdirSync(path.join(topicsDir, `dummy_folder_${i}`), { recursive: true });
    }

    const category = 'new-agencies';
    const filename = 'New_Agency';
    
    // This new category should be directed to misc because 95 >= threshold (95)
    const resolvedPath = resolveTopicPath(tempDir, category, filename, 100, 95);
    
    const expected = path.join(tempDir, 'topics', 'misc', 'New_Agency.md');
    assert.strictEqual(resolvedPath, expected);
    assert.ok(fs.existsSync(path.dirname(resolvedPath)));
    // Ensure the new category was NOT created
    assert.strictEqual(fs.existsSync(path.join(topicsDir, category)), false);
  });

  // Clean up
  if (fs.existsSync(tempDir)) {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
});
