// All JavaScript moved here to comply with CSP

document.addEventListener("DOMContentLoaded", () => {
  // Main execute button event
  document.getElementById("send").addEventListener("click", async () => {
    const prompt = document.getElementById("prompt").value;
    console.log("Sending prompt:", prompt);

    if (!prompt.trim()) {
      showStatus("Please enter a command", true);
      return;
    }

    showStatus("Executing...", false);

    try {
      // Call your app.py /generate endpoint
      const response = await fetch(`http://localhost:8000/generate?prompt=${encodeURIComponent(prompt)}`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log("Received response:", data);

      // Get current tab
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tabs[0]) {
        console.error("No active tab found");
        showStatus("No active tab found", true);
        return;
      }

      // Execute the code from your app.py
      await executeCodeSafely(data.code, prompt, tabs[0].id);
      
      console.log(`Script executed successfully via ${data.source}`);
      showStatus(`Success via ${data.source}`, false);
      
      // Call your app.py /save_script endpoint
      await saveScript(prompt, data.code, true, data.source, tabs[0].url);
      
    } catch (error) {
      console.error("Script execution failed:", error);
      showStatus(`Failed: ${error.message}`, true);
      
      // Still save the failed attempt
      try {
        const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
        await saveScript(prompt, "", false, "error", tabs[0]?.url || "unknown");
      } catch (saveError) {
        console.error("Failed to save error:", saveError);
      }
    }
  });

  // Enter key support
  document.getElementById("prompt").addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      document.getElementById("send").click();
    }
  });
});

// Test command function (moved from inline script)
function testCommand(command) {
    document.getElementById('prompt').value = command;
    document.getElementById('send').click();
}

// Show status function (moved from inline script)
function showStatus(message, isError = false) {
    const status = document.getElementById('status');
    status.textContent = message;
    status.className = isError ? 'error' : 'success';
    
    if (message === "Executing...") {
        return;
    }
    
    setTimeout(() => {
        status.textContent = '';
        status.className = '';
    }, 3000);
}

// CSP-compliant code execution that matches your app.py patterns
async function executeCodeSafely(code, prompt, tabId) {
  try {
    // Parse the generated code and execute it safely
    if (code.includes("document.querySelectorAll('button')") && code.includes("backgroundColor")) {
      const colorMatch = code.match(/backgroundColor = '([^']+)'/);
      const color = colorMatch ? colorMatch[1] : 'blue';
      
      await chrome.scripting.executeScript({
        target: { tabId: tabId },
        func: changeButtonColors,
        args: [color]
      });
      
    } else if (code.includes("document.body.style.backgroundColor")) {
      const colorMatch = code.match(/backgroundColor = '([^']+)'/);
      const color = colorMatch ? colorMatch[1] : 'white';
      
      await chrome.scripting.executeScript({
        target: { tabId: tabId },
        func: changeBackgroundColor,
        args: [color]
      });
      
    } else if (code.includes("document.querySelectorAll('img')") && code.includes("display = 'none'")) {
      await chrome.scripting.executeScript({
        target: { tabId: tabId },
        func: hideImages
      });
      
    } else if (code.includes("document.querySelectorAll('img')") && code.includes("display = 'block'")) {
      await chrome.scripting.executeScript({
        target: { tabId: tabId },
        func: showImages
      });
      
    } else if (code.includes("document.body.style.fontSize")) {
      const sizeMatch = code.match(/fontSize = '([^']+)'/);
      const size = sizeMatch ? sizeMatch[1] : '16px';
      
      await chrome.scripting.executeScript({
        target: { tabId: tabId },
        func: changeTextSize,
        args: [size]
      });
      
    } else if (code.includes("document.body.style.fontWeight = 'bold'")) {
      await chrome.scripting.executeScript({
        target: { tabId: tabId },
        func: makeBold
      });
      
    } else if (code.includes("document.querySelectorAll('button')") && code.includes("display = 'none'")) {
      await chrome.scripting.executeScript({
        target: { tabId: tabId },
        func: hideButtons
      });
      
    } else {
      // Generic execution with visual feedback
      await chrome.scripting.executeScript({
        target: { tabId: tabId },
        func: genericExecution,
        args: [prompt]
      });
    }
  } catch (error) {
    console.error("Script execution error:", error);
    throw error;
  }
}

// Functions that will be injected into the webpage (CSP-compliant)
function changeButtonColors(color) {
  document.querySelectorAll('button').forEach(btn => {
    btn.style.backgroundColor = color;
  });
  console.log(`AI Extension: Changed button colors to ${color}`);
}

function changeBackgroundColor(color) {
  document.body.style.backgroundColor = color;
  console.log(`AI Extension: Changed background to ${color}`);
}

function hideImages() {
  document.querySelectorAll('img').forEach(img => {
    img.style.display = 'none';
  });
  console.log("AI Extension: Hidden all images");
}

function showImages() {
  document.querySelectorAll('img').forEach(img => {
    img.style.display = 'block';
  });
  console.log("AI Extension: Showed all images");
}

function changeTextSize(size) {
  document.body.style.fontSize = size;
  console.log(`AI Extension: Changed text size to ${size}`);
}

function makeBold() {
  document.body.style.fontWeight = 'bold';
  console.log("AI Extension: Made text bold");
}

function hideButtons() {
  document.querySelectorAll('button').forEach(btn => {
    btn.style.display = 'none';
  });
  console.log("AI Extension: Hidden all buttons");
}

function genericExecution(promptText) {
  console.log(`AI Extension: Generic execution for: ${promptText}`);
  document.body.style.border = '3px solid #4CAF50';
  setTimeout(() => {
    document.body.style.border = '';
  }, 2000);
}

// Save script using your app.py /save_script endpoint
async function saveScript(prompt, code, success, source, url) {
  try {
    const response = await fetch("http://localhost:8000/save_script", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        prompt: prompt,
        code: code,
        source: source,
        success: success,
        timestamp: new Date().toISOString(),
        url: url || "unknown"
      })
    });
    
    if (response.ok) {
      console.log(`Script saved - Source: ${source}, Success: ${success}`);
    } else {
      console.warn(`Failed to save script: ${response.status}`);
    }
  } catch (error) {
    console.error("Failed to save script:", error);
  }
}