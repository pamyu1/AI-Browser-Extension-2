from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from transformers import pipeline
from datetime import datetime
import json
import os
import platform
import torch

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cross-platform device detection
def get_device():
    """Detect best device for current platform"""
    system = platform.system().lower()
    
    if torch.cuda.is_available():
        print("Using CUDA (NVIDIA GPU)")
        return "cuda"
    elif system == "darwin" and hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        print("Using MPS (Apple Silicon)")
        return "mps"
    else:
        print("Using CPU")
        return "cpu"

# Load model with cross-platform device support
print(f"Platform: {platform.system()} {platform.machine()}")
device = get_device()

# Initialize generator as global variable
generator = None

# Load AI model pipeline
try:
    print("Loading AI model pipeline...")
    generator = pipeline(
        "text-generation",
        model="Salesforce/codet5p-770m",  # or try "microsoft/CodeGPT-small-py"
        device=device,
        max_length=512
    )
    print(f"✅ AI model pipeline loaded successfully on {device}")
except Exception as e:
    print(f"❌ Failed to load AI model: {e}")
    generator = None
    print("🔄 Falling back to pattern-based system (100% reliable)")

def enhance_prompt_for_codet5(user_prompt):
    """Better prompts for CodeT5+ model"""
    prompt_lower = user_prompt.lower()
    
    # CodeT5+ works better with simpler, more direct prompts
    if "button" in prompt_lower and any(color in prompt_lower for color in ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'pink']):
        color = extract_color(user_prompt)
        return f"document.querySelectorAll('button').forEach(btn => btn.style.backgroundColor = '{color}'"
    elif "background" in prompt_lower and any(color in prompt_lower for color in ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'pink']):
        color = extract_color(user_prompt)
        return f"document.body.style.backgroundColor = '{color}'"
    elif "hide" in prompt_lower and "image" in prompt_lower:
        return f"document.querySelectorAll('img').forEach(img => img.style.display = 'none'"
    elif "hide" in prompt_lower and "button" in prompt_lower:
        return f"document.querySelectorAll('button').forEach(btn => btn.style.display = 'none'"
    else:
        return f"document.querySelectorAll"

def extract_color(text):
    """Extract color from user input"""
    colors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'pink', 'black', 'white', 'gray', 'grey', 'brown', 'cyan', 'magenta', 'lime', 'navy', 'maroon', 'olive', 'teal', 'silver', 'gold', 'lightpink', 'lightblue', 'lightgreen']
    text_lower = text.lower()
    
    # Check for compound colors first (lightpink, lightblue, etc.)
    for color in sorted(colors, key=len, reverse=True):
        if color in text_lower:
            return color
    return 'blue'  # default

@app.get("/generate")
def generate_code(prompt: str = Query(...)):
    global generator  # Add this line to access global variable
    
    if generator is None:
        fallback_code = generate_fallback_code(prompt)
        print(f"Using fallback pattern for: {prompt}")
        print(f"Generated fallback code: {fallback_code}")
        return {"code": fallback_code, "source": "fallback", "prompt": prompt, "timestamp": datetime.now().isoformat()}
    
    # Test model on first use (safer check)
    if not hasattr(generate_code, 'model_tested'):
        generate_code.model_tested = True
        try:
            if not test_model_quality(generator, ["test"]):
                print("Model failed quality test - disabling AI")
                generator = None
                fallback_code = generate_fallback_code(prompt)
                print(f"Using fallback pattern for: {prompt}")
                print(f"Generated fallback code: {fallback_code}")
                return {"code": fallback_code, "source": "fallback", "prompt": prompt, "timestamp": datetime.now().isoformat()}
        except Exception as e:
            print(f"Model testing failed: {e} - disabling AI")
            generator = None
            fallback_code = generate_fallback_code(prompt)
            print(f"Using fallback pattern for: {prompt}")
            print(f"Generated fallback code: {fallback_code}")
            return {"code": fallback_code, "source": "fallback", "prompt": prompt, "timestamp": datetime.now().isoformat()}
    
    try:
        enhanced_prompt = enhance_prompt_for_codet5(prompt)
        print(f"Original prompt: {prompt}")
        print(f"Enhanced prompt: {enhanced_prompt}")
        
        # CodeT5+ compatible parameters
        generation_params = {
            "max_new_tokens": 40,
            "num_return_sequences": 1,
            "do_sample": True,
            "top_p": 0.85,
            "repetition_penalty": 1.1,
            "truncation": True,
            "pad_token_id": 0
        }
        
        result = generator(enhanced_prompt, **generation_params)
        full_text = result[0]['generated_text']
        code = full_text.replace(enhanced_prompt, "").strip()
        
        print(f"Raw AI output: {repr(code)}")
        
        # Try to complete the code if it looks promising
        if code and len(code) > 5:
            # Clean up and try to complete partial JavaScript
            code = code.replace('\n', ' ').strip()
            
            # Add missing closing parts
            if 'forEach' in code and not code.endswith(');'):
                if not code.endswith("'"):
                    code += "');"
                else:
                    code += ");"
            elif 'style.' in code and not code.endswith(';'):
                if not code.endswith("'"):
                    code += "';"
                else:
                    code += ";"
            
            # Validation for completed code
            if (code and 
                len(code) > 15 and
                'document.' in code and
                ('style.' in code or 'querySelector' in code) and
                code.endswith(';') and
                not any(bad in code.lower() for bad in ['def ', 'import ', 'print(', 'class ', '</', 'html'])):
                
                print(f"Generated AI code: {code}")
                return {"code": code, "source": "ai", "prompt": prompt, "timestamp": datetime.now().isoformat()}
        
        print(f"AI generated invalid code, using fallback")
        
    except Exception as e:
        print(f"AI model failed: {e}, using fallback")
    
    fallback_code = generate_fallback_code(prompt)
    print(f"Using fallback pattern for: {prompt}")
    print(f"Generated fallback code: {fallback_code}")
    return {"code": fallback_code, "source": "fallback", "prompt": prompt, "timestamp": datetime.now().isoformat()}

def generate_fallback_code(prompt):
    """Generate reliable fallback code with enhanced patterns"""
    prompt_lower = prompt.lower()
    
    # Extract color
    found_color = extract_color(prompt)
    
    # Enhanced pattern matching
    if "button" in prompt_lower and found_color:
        return f"document.querySelectorAll('button').forEach(btn => btn.style.backgroundColor = '{found_color}');"
    elif "background" in prompt_lower and found_color:
        return f"document.body.style.backgroundColor = '{found_color}';"
    elif "text" in prompt_lower and found_color and "color" in prompt_lower:
        return f"document.body.style.color = '{found_color}';"
    elif "hide" in prompt_lower and ("button" in prompt_lower):
        return "document.querySelectorAll('button').forEach(btn => btn.style.display = 'none');"
    elif "show" in prompt_lower and ("button" in prompt_lower):
        return "document.querySelectorAll('button').forEach(btn => btn.style.display = 'block');"
    elif "hide" in prompt_lower and ("image" in prompt_lower or "img" in prompt_lower):
        return "document.querySelectorAll('img').forEach(img => img.style.display = 'none');"
    elif "show" in prompt_lower and ("image" in prompt_lower or "img" in prompt_lower):
        return "document.querySelectorAll('img').forEach(img => img.style.display = 'block');"
    elif ("small" in prompt_lower or "smaller" in prompt_lower) and "image" in prompt_lower:
        return "document.querySelectorAll('img').forEach(img => img.style.width = '50px');"
    elif ("big" in prompt_lower or "larger" in prompt_lower) and "image" in prompt_lower:
        return "document.querySelectorAll('img').forEach(img => img.style.width = '200px');"
    elif "text" in prompt_lower and ("big" in prompt_lower or "larger" in prompt_lower):
        return "document.body.style.fontSize = '20px';"
    elif "text" in prompt_lower and ("small" in prompt_lower or "smaller" in prompt_lower):
        return "document.body.style.fontSize = '12px';"
    elif "bold" in prompt_lower:
        return "document.body.style.fontWeight = 'bold';"
    elif "italic" in prompt_lower:
        return "document.body.style.fontStyle = 'italic';"
    else:
        return f"console.log('Extension executed: {prompt}'); document.body.style.border = '2px solid green'; setTimeout(() => document.body.style.border = '', 2000);"

# Cross-platform file handling
def get_scripts_file_path():
    """Get platform-appropriate path for scripts file"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "working_scripts.json")

@app.post("/save_script")
def save_script(script_data: dict):
    try:
        scripts_file = get_scripts_file_path()
        
        # Load existing scripts
        if os.path.exists(scripts_file):
            with open(scripts_file, 'r', encoding='utf-8') as f:
                scripts = json.load(f)
        else:
            scripts = []
        
        # Add new script
        script_entry = {
            "id": len(scripts) + 1,
            "prompt": script_data.get("prompt"),
            "code": script_data.get("code"),
            "source": script_data.get("source", "unknown"),
            "success": script_data.get("success"),
            "timestamp": script_data.get("timestamp"),
            "url": script_data.get("url", "unknown"),
            "platform": platform.system()
        }
        scripts.append(script_entry)
        
        # Save to file with UTF-8 encoding
        with open(scripts_file, 'w', encoding='utf-8') as f:
            json.dump(scripts, f, indent=2, ensure_ascii=False)
        
        print(f"Saved script #{script_entry['id']}: {script_data.get('prompt')}")
        return {"message": "Script saved successfully", "id": script_entry["id"]}
    except Exception as e:
        print(f"Error saving script: {e}")
        return {"error": str(e)}

@app.get("/get_saved_scripts")
def get_saved_scripts():
    try:
        scripts_file = get_scripts_file_path()
        with open(scripts_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

@app.get("/export_tampermonkey/{script_id}")
def export_tampermonkey(script_id: int):
    try:
        scripts_file = get_scripts_file_path()
        with open(scripts_file, 'r', encoding='utf-8') as f:
            scripts = json.load(f)
        
        script = next((s for s in scripts if s["id"] == script_id), None)
        if not script:
            return {"error": "Script not found"}
        
        # Clean filename for cross-platform compatibility
        safe_filename = "".join(c for c in script["prompt"] if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_filename = safe_filename.replace(' ', '_')
        
        tampermonkey_script = f"""// ==UserScript==
// @name         Auto-generated: {script["prompt"]}
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Generated by AI Browser Extension
// @author       You
// @match        *://*/*
// @grant        none
// ==/UserScript==

(function() {{
    'use strict';
    
    // Generated code for: {script["prompt"]}
    // Source: {script.get("source", "unknown")}
    // Platform: {script.get("platform", "unknown")}
    {script["code"]}
    
    console.log('Tampermonkey script executed: {script["prompt"]}');
}})();"""
        
        return {
            "tampermonkey_script": tampermonkey_script,
            "filename": f"script_{script_id}_{safe_filename}.user.js"
        }
    except Exception as e:
        return {"error": str(e)}

# Add system info endpoint
@app.get("/system_info")
def get_system_info():
    return {
        "platform": platform.system(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
        "device": device,
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "mps_available": hasattr(torch.backends, 'mps') and torch.backends.mps.is_available() if platform.system() == "Darwin" else False
    }

def test_model_quality(generator, test_prompts):
    """Test if model actually generates useful JavaScript"""
    if generator is None:
        return False
    
    test_cases = [
        "document.querySelector('button').style.backgroundColor = 'red'",
        "document.body.style.fontSize = '20px'",
        "document.querySelectorAll('img').forEach(img => img.style.display = 'none'"
    ]
    
    success_count = 0
    for prompt in test_cases:
        try:
            result = generator(prompt, max_new_tokens=20, do_sample=False)
            output = result[0]['generated_text'].replace(prompt, "").strip()
            
            # Check if completion makes sense
            if (output and 
                len(output) > 2 and 
                not any(bad in output.lower() for bad in ['import', 'def ', 'class ', 'apache', 'license']) and
                any(good in output.lower() for good in [';', ')', '}', "'"])):
                success_count += 1
                print(f"✅ Test passed: {prompt} → {output[:30]}...")
            else:
                print(f"❌ Test failed: {prompt} → {output[:30]}...")
                
        except Exception as e:
            print(f"❌ Test error: {e}")
    
    success_rate = success_count / len(test_cases)
    print(f"Model quality: {success_rate:.1%} success rate")
    return success_rate > 0.5  # Require >50% success

# Add this alternative to AI models:

def smart_completion(prompt_start):
    """Smart rule-based completion for JavaScript"""
    prompt_start = prompt_start.strip()
    
    # Common JavaScript completion patterns
    completions = {
        "document.querySelectorAll('button').forEach(btn => btn.style.backgroundColor = '": "red');",
        "document.querySelectorAll('img').forEach(img => img.style.display = '": "none');",
        "document.body.style.backgroundColor = '": "white';",
        "document.body.style.fontSize = '": "16px';",
        "document.body.style.fontWeight = '": "bold';",
        "document.querySelectorAll('button').forEach(btn => btn.style.display = '": "none');"
    }
    
    # Find best match
    for pattern, completion in completions.items():
        if prompt_start.startswith(pattern):
            return prompt_start + completion
    
    # Generic completion
    if "forEach" in prompt_start and not prompt_start.endswith(");"):
        return prompt_start + ");"
    elif "style." in prompt_start and not prompt_start.endswith(";"):
        return prompt_start + ";"
    
    return prompt_start + ";"

if __name__ == "__main__":
    import uvicorn
    print(f"Starting server on {platform.system()} with device: {device}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
