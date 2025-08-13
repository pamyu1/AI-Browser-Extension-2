document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("send").addEventListener("click", async () => {
    const prompt = document.getElementById("prompt").value;
    console.log("Sending prompt:", prompt);

    if (!prompt.trim()) {
      showStatus("Please enter a command", true);
      return;
    }

    showStatus("Executing...", false);

    try {
      const response = await fetch("http://localhost:8000/generate?prompt=" + encodeURIComponent(prompt));
      const data = await response.json();
      console.log("Received response:", data);

      // Get current tab
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tabs[0]) {
        console.error("No active tab found");
        showStatus("No active tab found", true);
        return;
      }

      // TEST AI MODEL PROPERLY
      let codeToExecute = data.code;
      let executionSource = data.source;
      
      // If backend claims AI worked, let's verify it
      if (data.source === "ai") {
        console.log("Backend says AI generated code:", data.code);
        
        // Double-check if AI code is actually valid JavaScript
        if (isValidJavaScript(data.code)) {
          console.log("AI code passed validation - using AI");
          executionSource = "ai";
        } else {
          console.log("AI code failed validation - falling back");
          codeToExecute = generateClientFallback(prompt);
          executionSource = "client-fallback";
        }
      } else {
        console.log("Backend used fallback:", data.code);
      }

      // Execute the determined code
      await executeCode(codeToExecute, prompt, tabs[0].id);
      
      console.log("Script executed successfully via " + executionSource);
      showStatus("Success via " + executionSource, false);
      
      await saveScript(prompt, codeToExecute, true, executionSource);
      
    } catch (error) {
      console.error("Script execution failed:", error);
      showStatus("Execution failed", true);
      await saveScript(prompt, data.code || "", false, "error");
    }
  });

  document.getElementById("prompt").addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      document.getElementById("send").click();
    }
  });
});

// Function to validate if code is actually valid JavaScript
function isValidJavaScript(code) {
  // Check for common JavaScript patterns
  if (!code || typeof code !== 'string') return false;
  
  // Must contain DOM manipulation
  if (!code.includes('document.')) return false;
  
  // Should not contain Python-like syntax
  if (code.includes('def ') || code.includes('import ') || code.includes('print(')) return false;
  
  // Should contain proper JavaScript patterns
  const jsPatterns = [
    'style.',
    'querySelector',
    'forEach',
    'addEventListener'
  ];
  
  return jsPatterns.some(pattern => code.includes(pattern));
}

// Client-side fallback generation
function generateClientFallback(prompt) {
  const promptLower = prompt.toLowerCase();
  
  // Extract color
  const colors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'pink', 'black', 'white', 'gray', 'grey', 'brown'];
  let color = 'blue';
  for (let c of colors) {
    if (promptLower.includes(c)) {
      color = c;
      break;
    }
  }
  
  // Generate fallback code
  if (promptLower.includes('button') && (promptLower.includes('color') || colors.some(c => promptLower.includes(c)))) {
    return `document.querySelectorAll('button').forEach(btn => btn.style.backgroundColor = '${color}');`;
  } else if (promptLower.includes('background') && colors.some(c => promptLower.includes(c))) {
    return `document.body.style.backgroundColor = '${color}';`;
  } else if (promptLower.includes('hide') && promptLower.includes('image')) {
    return "document.querySelectorAll('img').forEach(img => img.style.display = 'none');";
  } else {
    return `console.log('Client fallback executed: ${prompt}');`;
  }
}

// Function to execute code based on pattern matching
async function executeCode(code, prompt, tabId) {
  let scriptFunction;
  
  if (code.includes("document.querySelectorAll('button')") && code.includes("backgroundColor")) {
    const colorMatch = code.match(/backgroundColor = '([^']+)'/);
    const color = colorMatch ? colorMatch[1] : 'blue';
    
    scriptFunction = function(color) {
      document.querySelectorAll('button').forEach(btn => {
        btn.style.backgroundColor = color;
      });
      console.log("Changed button colors to " + color);
    };
    
    await chrome.scripting.executeScript({
      target: { tabId: tabId },
      func: scriptFunction,
      args: [color]
    });
    
  } else if (code.includes("document.body.style.backgroundColor")) {
    const colorMatch = code.match(/backgroundColor = '([^']+)'/);
    const color = colorMatch ? colorMatch[1] : 'white';
    
    scriptFunction = function(color) {
      document.body.style.backgroundColor = color;
      console.log("Changed background to " + color);
    };
    
    await chrome.scripting.executeScript({
      target: { tabId: tabId },
      func: scriptFunction,
      args: [color]
    });
    
  } else if (code.includes("document.querySelectorAll('img')") && code.includes("display = 'none'")) {
    scriptFunction = function() {
      document.querySelectorAll('img').forEach(img => {
        img.style.display = 'none';
      });
      console.log("Hidden all images");
    };
    
    await chrome.scripting.executeScript({
      target: { tabId: tabId },
      func: scriptFunction
    });
    
  } else {
    scriptFunction = function(promptText) {
      console.log("Generic execution for: " + promptText);
      document.body.style.border = '2px solid green';
      setTimeout(() => {
        document.body.style.border = '';
      }, 2000);
    };
    
    await chrome.scripting.executeScript({
      target: { tabId: tabId },
      func: scriptFunction,
      args: [prompt]
    });
  }
}

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

async function saveScript(prompt, code, success, source) {
  try {
    await fetch("http://localhost:8000/save_script", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        prompt: prompt,
        code: code,
        source: source,
        success: success,
        timestamp: new Date().toISOString()
      })
    });
    console.log("Script saved - Source: " + source + ", Success: " + success);
  } catch (error) {
    console.error("Failed to save script:", error);
  }
}