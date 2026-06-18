"use client";

import { ChevronDown, ChevronRight, File, Folder, FolderOpen } from "lucide-react";
import { useState } from "react";

export type FileTreeNode = {
  path: string;
  name: string;
  kind: "file" | "directory";
  size_bytes: number;
  children?: FileTreeNode[];
};

function buildTree(nodes: FileTreeNode[]): FileTreeNode[] {
  const root: FileTreeNode[] = [];
  const dirMap = new Map<string, FileTreeNode>();

  for (const node of nodes) {
    const parts = node.path.split("/");
    let current = root;

    for (let i = 0; i < parts.length; i++) {
      const isLast = i === parts.length - 1;
      const partPath = parts.slice(0, i + 1).join("/");

      if (isLast) {
        current.push({ ...node, name: parts[i] });
      } else {
        let dir = dirMap.get(partPath);
        if (!dir) {
          dir = {
            path: partPath,
            name: parts[i],
            kind: "directory",
            size_bytes: 0,
            children: [],
          };
          dirMap.set(partPath, dir);
          current.push(dir);
        }
        current = dir.children!;
      }
    }
  }
  return root;
}

type FileTreeProps = {
  files: FileTreeNode[];
  activePath: string;
  onSelect: (path: string) => void;
};

function TreeRow({
  node,
  depth,
  activePath,
  onSelect,
}: {
  node: FileTreeNode;
  depth: number;
  activePath: string;
  onSelect: (path: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const isDir = node.kind === "directory";
  const isActive = node.path === activePath;
  const children = node.children ?? [];
  const Icon = isDir ? (open ? FolderOpen : Folder) : File;
  const paddingLeft = 8 + depth * 14;

  return (
    <>
      <button
        type="button"
        className={`file-tree-row ${isActive ? "active" : ""}`}
        style={{ paddingLeft }}
        onClick={() => {
          if (isDir) {
            setOpen(!open);
          } else {
            onSelect(node.path);
          }
        }}
      >
        <span className="file-tree-icon">
          {isDir && children.length > 0 ? (
            open ? <ChevronDown size={12} /> : <ChevronRight size={12} />
          ) : (
            <span style={{ width: 12 }} />
          )}
          <Icon size={14} />
        </span>
        <span className="file-tree-name">{node.name}</span>
      </button>
      {isDir && open &&
        children.map((child) => (
          <TreeRow
            key={child.path}
            node={child}
            depth={depth + 1}
            activePath={activePath}
            onSelect={onSelect}
          />
        ))}
    </>
  );
}

export function FileTree({ files, activePath, onSelect }: FileTreeProps) {
  const tree = buildTree(files);

  return (
    <div className="file-tree">
      {tree.map((node) => (
        <TreeRow
          key={node.path}
          node={node}
          depth={0}
          activePath={activePath}
          onSelect={onSelect}
        />
      ))}
    </div>
  );
}
