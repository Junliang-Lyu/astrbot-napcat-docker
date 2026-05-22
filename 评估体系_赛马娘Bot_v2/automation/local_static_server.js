const http = require("http");
const fs = require("fs");
const path = require("path");

const root = __dirname;
const port = Number(process.argv[2] || 18974);
const host = "127.0.0.1";

const contentTypes = {
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".txt": "text/plain; charset=utf-8"
};

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "authorization, content-type, accept, origin, x-requested-with",
  "Access-Control-Max-Age": "86400"
};

const server = http.createServer((req, res) => {
  if (req.method === "OPTIONS") {
    res.writeHead(204, corsHeaders);
    res.end();
    return;
  }

  const url = new URL(req.url, `http://${host}:${port}`);
  const pathname = decodeURIComponent(url.pathname).replace(/^\/+/, "");
  const target = path.resolve(root, pathname || "README_自动测试.md");

  if (!target.startsWith(root) || !fs.existsSync(target) || fs.statSync(target).isDirectory()) {
    res.writeHead(404, { ...corsHeaders, "Content-Type": "text/plain; charset=utf-8" });
    res.end("not found");
    return;
  }

  res.writeHead(200, {
    ...corsHeaders,
    "Cache-Control": "no-store",
    "Content-Type": contentTypes[path.extname(target)] || "application/octet-stream"
  });
  fs.createReadStream(target).pipe(res);
});

server.listen(port, host, () => {
  console.log(`serving ${root} at http://${host}:${port}/`);
});
