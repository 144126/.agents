// set a file on the X chat composer's file input, which sits inside a shadow root agent-browser selectors cannot reach
const [, , url_part, file] = process.argv
const page = (await (await fetch("http://127.0.0.1:9223/json")).json()).find((t) => t.type === "page" && t.url.includes(url_part))
if (!page) throw new Error("no page matching " + url_part)
const ws = new WebSocket(page.webSocketDebuggerUrl)
const pending = new Map()
let n = 0
const send = (method, params = {}) =>
  new Promise((ok, fail) => {
    pending.set(++n, { ok, fail })
    ws.send(JSON.stringify({ id: n, method, params }))
  })
ws.onmessage = (ev) => {
  const m = JSON.parse(ev.data)
  const p = pending.get(m.id)
  if (!p) return
  pending.delete(m.id)
  m.error ? p.fail(new Error(JSON.stringify(m.error))) : p.ok(m.result)
}
await new Promise((ok) => (ws.onopen = ok))
const found = await send("Runtime.evaluate", {
  expression: `(()=>{let f=null;const walk=r=>{for(const e of r.querySelectorAll("*")){if(f)return;if(e.tagName==="INPUT"&&e.type==="file"&&e.dataset.testid==="dm-composer-file-input"){f=e;return}if(e.shadowRoot)walk(e.shadowRoot)}};walk(document);return f})()`,
})
if (!found.result.objectId) throw new Error("file input not found")
await send("DOM.enable")
await send("DOM.setFileInputFiles", { files: [file], objectId: found.result.objectId })
console.log("attached", file)
ws.close()
