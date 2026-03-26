async function getActiveTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs[0];
}

function setStatus(msg) {
  const status = document.getElementById("status");
  status.textContent = msg;
}

async function collectLinksFromPage(tabId) {
  return chrome.tabs.sendMessage(tabId, { type: "collect-links" });
}

async function requestDownloads(payload) {
  return chrome.runtime.sendMessage({ type: "download-links", payload });
}

document.getElementById("download-current").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  setStatus("Scanning current page...");

  try {
    const activeTab = await getActiveTab();
    if (!activeTab || typeof activeTab.id !== "number") {
      throw new Error("Could not detect active tab.");
    }

    const collected = await collectLinksFromPage(activeTab.id);
    if (!collected || !collected.ok) {
      throw new Error("Could not parse Blackboard links on this page.");
    }

    const links = collected.data.links || [];
    if (links.length === 0) {
      setStatus("No downloadable links found on this page.");
      return;
    }

    setStatus(`Found ${links.length} link(s). Starting download...`);
    const result = await requestDownloads(collected.data);
    if (!result || !result.ok) {
      throw new Error(result && result.error ? result.error : "Download failed.");
    }

    setStatus(`Queued ${result.count} download(s).`);
  } catch (err) {
    setStatus(`Error: ${String(err)}`);
  } finally {
    button.disabled = false;
  }
});
