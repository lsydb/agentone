/**
 * 文章拾光 - 前端交互逻辑
 */

const $ = (sel) => document.querySelector(sel);

function showError(msg) {
  const el = $("#errorMsg");
  el.textContent = msg;
  el.classList.add("active");
  setTimeout(() => el.classList.remove("active"), 4000);
}

function setLoading(isLoading) {
  $("#loading").classList.toggle("active", isLoading);
  $("#submitBtn").disabled = isLoading;
  $("#submitBtn").textContent = isLoading ? "拾取中……" : "开始拾取";
}

function showResults(data) {
  $("#articleTitle").textContent = data.title;
  $("#articleAuthor").textContent = data.author;
  $("#originalBody").textContent = data.original;
  $("#summaryBody").textContent = data.summary;

  $("#inputCard").style.display = "none";
  $("#results").classList.add("active");

  // 滚动到结果区
  $("#results").scrollIntoView({ behavior: "smooth", block: "start" });
}

function resetForm() {
  $("#url").value = "";
  $("#apiKey").value = "";
  $("#inputCard").style.display = "block";
  $("#results").classList.remove("active");
  $("#errorMsg").classList.remove("active");
}

async function handleSubmit() {
  const url = $("#url").value.trim();
  const apiKey = $("#apiKey").value.trim();

  if (!url) {
    showError("请输入文章链接");
    return;
  }
  if (!apiKey) {
    showError("请输入 Kimi API Key");
    return;
  }

  setLoading(true);

  try {
    const resp = await fetch("/api/fetch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, apiKey }),
    });

    const data = await resp.json();

    if (!resp.ok) {
      throw new Error(data.error || `请求失败 (${resp.status})`);
    }

    showResults(data);
  } catch (err) {
    showError(err.message);
  } finally {
    setLoading(false);
  }
}

// 支持回车提交
$("#url").addEventListener("keydown", (e) => {
  if (e.key === "Enter") $("#apiKey").focus();
});
$("#apiKey").addEventListener("keydown", (e) => {
  if (e.key === "Enter") handleSubmit();
});
