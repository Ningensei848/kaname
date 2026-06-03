import * as fs from 'fs';
import * as path from 'path';

export function resolveTopicPath(
  baseDir: string,
  category: string,
  fileName: string,
  maxDirs = 100,
  fallbackLimit = 95
): string {
  // Ensure the base directory exists
  const topicsDir = path.join(baseDir, 'topics');
  if (!fs.existsSync(topicsDir)) {
    fs.mkdirSync(topicsDir, { recursive: true });
  }

  // Clean category and filename
  const cleanCategory = sanitizeName(category || 'misc');
  const cleanFileName = sanitizeName(fileName);
  const targetDir = path.join(topicsDir, cleanCategory);

  // If the target directory already exists, we can use it immediately.
  if (fs.existsSync(targetDir)) {
    return path.join(targetDir, `${cleanFileName}.md`);
  }

  // Target directory doesn't exist, check subdirectory count.
  const currentSubdirs = getSubdirectories(topicsDir);

  if (currentSubdirs.length >= fallbackLimit) {
    console.warn(
      `Directory limit reached (${currentSubdirs.length} >= ${fallbackLimit}). Falling back to 'topics/misc/' folder to protect against folder sprawl.`
    );
    const fallbackDir = path.join(topicsDir, 'misc');
    if (!fs.existsSync(fallbackDir)) {
      fs.mkdirSync(fallbackDir, { recursive: true });
    }
    return path.join(fallbackDir, `${cleanFileName}.md`);
  }

  // Below threshold, safe to create the new category directory
  fs.mkdirSync(targetDir, { recursive: true });
  return path.join(targetDir, `${cleanFileName}.md`);
}

function getSubdirectories(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir, { withFileTypes: true })
    .filter(dirent => dirent.isDirectory())
    .map(dirent => dirent.name);
}

function sanitizeName(name: string): string {
  // Replace invalid filesystem characters and whitespace
  return name
    .replace(/[\\/:*?"<>|]/g, '_')
    .replace(/\s+/g, '_')
    .trim();
}
