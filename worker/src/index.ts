// Cloudflare Worker for skills.ydb.sh
//
// Routing:
//   GET /                      → install.sh (CLI) or landing page (browser)
//   GET /install.sh            → install.sh from main
//   GET /v0.1.0                → install.sh from tag v0.1.0 (CLI) or landing (browser)
//   GET /v0.1.0/install.sh     → install.sh from tag v0.1.0
//   GET /some-branch/file.md   → file from branch
//   GET /*                     → proxy from main

interface Env {
  GITHUB_REPO: string;
}

const DEFAULT_REF = "main";
const GITHUB_RAW = "https://raw.githubusercontent.com";

const CLI_USER_AGENTS = [
  "curl",
  "wget",
  "httpie",
  "fetch",
  "powershell",
  "python-requests",
  "python-urllib",
  "go-http-client",
  "ruby",
  "perl",
  "aria2",
  "lwp-request",
  "undici",
  "node-fetch",
  "axios",
  "got",
];

function isCLI(request: Request): boolean {
  const ua = (request.headers.get("user-agent") || "").toLowerCase();
  if (!ua) return true;
  return CLI_USER_AGENTS.some((cli) => ua.includes(cli));
}

// Parse path into { ref, filePath }
// /v0.1.0/install.sh → { ref: "v0.1.0", filePath: "/install.sh" }
// /install.sh         → { ref: "main",   filePath: "/install.sh" }
// /v0.1.0             → { ref: "v0.1.0", filePath: "" }
// /my-branch          → { ref: "main",   filePath: "/my-branch" }
function parsePath(pathname: string): { ref: string; filePath: string } {
  const parts = pathname.replace(/^\/+/, "").split("/");
  if (parts.length === 0 || (parts.length === 1 && parts[0] === "")) {
    return { ref: DEFAULT_REF, filePath: "" };
  }

  const first = parts[0];

  // Version tag: starts with "v" followed by a digit (v0.1.0, v1, v2.3)
  // or branch names that don't look like files (no dots except version patterns)
  const isVersion = /^v\d/.test(first);

  if (isVersion) {
    const rest = parts.slice(1).join("/");
    return { ref: first, filePath: rest ? `/${rest}` : "" };
  }

  return { ref: DEFAULT_REF, filePath: pathname };
}

async function fetchFromGitHub(
  repo: string,
  ref: string,
  path: string,
  contentType: string,
): Promise<Response> {
  const url = `${GITHUB_RAW}/${repo}/${ref}${path}`;

  const response = await fetch(url, {
    headers: { "User-Agent": "ydb-skills-worker" },
  });

  if (!response.ok) {
    return new Response(`Not found: ${ref}${path}\n`, { status: 404 });
  }

  const body = await response.text();

  return new Response(body, {
    status: 200,
    headers: {
      "Content-Type": contentType,
      "Cache-Control": "public, max-age=300, s-maxage=600",
      "X-Source-Ref": ref,
      "Access-Control-Allow-Origin": "*",
    },
  });
}

import landing from "./landing.html";

function landingPage(ref: string): Response {
  const version = ref === DEFAULT_REF ? "latest" : ref;
  const versionPath = ref === DEFAULT_REF ? "" : `/${ref}`;

  const html = landing
    .replaceAll("{{version}}", version)
    .replaceAll("{{versionPath}}", versionPath);

  return new Response(html, {
    status: 200,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "public, max-age=300, s-maxage=600",
    },
  });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const { ref, filePath } = parsePath(url.pathname);

    // Explicit /install.sh → always serve script
    if (filePath === "/install.sh") {
      return fetchFromGitHub(
        env.GITHUB_REPO,
        ref,
        "/install.sh",
        "text/plain; charset=utf-8",
      );
    }

    // Root of a version or root of site → content negotiation
    if (filePath === "" || filePath === "/") {
      if (isCLI(request)) {
        return fetchFromGitHub(
          env.GITHUB_REPO,
          ref,
          "/install.sh",
          "text/plain; charset=utf-8",
        );
      }
      return landingPage(ref);
    }

    // Everything else → proxy from GitHub
    return fetchFromGitHub(
      env.GITHUB_REPO,
      ref,
      filePath,
      "text/plain; charset=utf-8",
    );
  },
} satisfies ExportedHandler<Env>;
