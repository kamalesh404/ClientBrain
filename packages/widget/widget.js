/** ClientBrain embeddable widget — <script src="widget.js" data-key="demo"> */
(function () {
  const key = document.currentScript?.dataset.key || "demo";
  const api = document.currentScript?.dataset.api || "http://localhost:8000";
  const btn = document.createElement("button");
  btn.textContent = "💬 Chat";
  btn.style.cssText = "position:fixed;bottom:20px;right:20px;z-index:9999;padding:12px 18px;border-radius:999px;border:none;background:#111;color:#fff;cursor:pointer";
  const box = document.createElement("div");
  box.style.cssText = "position:fixed;bottom:70px;right:20px;width:320px;height:400px;background:#fff;border:1px solid #ddd;border-radius:12px;display:none;flex-direction:column;z-index:9999;overflow:hidden";
  box.innerHTML = `<div style="padding:10px;background:#111;color:#fff">ClientBrain <small>${key}</small></div><div id="cb-msgs" style="flex:1;overflow:auto;padding:10px;font:14px system-ui"></div><div style="display:flex"><input id="cb-in" style="flex:1;padding:10px" placeholder="Ask..."/><button id="cb-send" style="padding:10px">➤</button></div>`;
  document.body.append(btn, box);
  btn.onclick = () => (box.style.display = box.style.display === "none" ? "flex" : "none");
  box.querySelector("#cb-send").onclick = async () => {
    const inp = box.querySelector("#cb-in");
    const msgs = box.querySelector("#cb-msgs");
    const q = inp.value; inp.value = "";
    msgs.innerHTML += `<div><b>You:</b> ${q}</div>`;
    const r = await fetch(`${api}/v1/chat`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workspace: key, message: q }) });
    const j = await r.json();
    msgs.innerHTML += `<div><b>Bot:</b> ${(j.answer || "").slice(0, 800)}</div>`;
  };
})();
