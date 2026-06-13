<#
.SYNOPSIS
Sets up the local Ollama environment for LexVerify.

.DESCRIPTION
This script:
1. Verifies Ollama is installed and running
2. Pulls the nomic-embed-text embedding model
3. Creates the custom LexVerify legal LLM from the GGUF file (if present)
   Otherwise, pulls the base llama3.2 model as a fallback.
4. Runs a smoke test.
#>

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "LexVerify Local LLM Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Check if Ollama is installed
try {
    $version = ollama -v
    Write-Host "✅ Found $version" -ForegroundColor Green
} catch {
    Write-Host "❌ Ollama is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install from https://ollama.com/download first." -ForegroundColor Yellow
    exit 1
}

# 2. Check if Ollama is running
try {
    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -ErrorAction Stop
    Write-Host "✅ Ollama service is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Ollama service is not running." -ForegroundColor Red
    Write-Host "Please start Ollama and try again." -ForegroundColor Yellow
    exit 1
}

# 3. Pull embedding model
Write-Host "`nPulling embedding model (nomic-embed-text)..." -ForegroundColor Cyan
ollama pull nomic-embed-text

# 4. Set up the LLM
$GGUF_PATH = "ollama\lexverify-legal-3b.Q4_K_M.gguf"
$MODEL_NAME = "lexverify-legal"

if (Test-Path $GGUF_PATH) {
    Write-Host "`nFound custom fine-tuned GGUF model: $GGUF_PATH" -ForegroundColor Green
    Write-Host "Building custom Ollama model '$MODEL_NAME'..." -ForegroundColor Cyan
    ollama create $MODEL_NAME -f ollama\Modelfile
} else {
    Write-Host "`n⚠️ Custom GGUF model not found at $GGUF_PATH" -ForegroundColor Yellow
    Write-Host "If you haven't fine-tuned the model yet, run the Colab notebook first." -ForegroundColor Yellow
    Write-Host "Falling back to base Llama 3.2 model for now..." -ForegroundColor Cyan
    
    # Modify the Modelfile to use the base model temporarily
    $modelfileContent = Get-Content ollama\Modelfile
    $modelfileContent[0] = "FROM llama3.2"
    $modelfileContent | Set-Content ollama\Modelfile.fallback
    
    ollama pull llama3.2
    ollama create $MODEL_NAME -f ollama\Modelfile.fallback
    Remove-Item ollama\Modelfile.fallback
}

# 5. Smoke test
Write-Host "`nRunning smoke test..." -ForegroundColor Cyan
try {
    $testResult = ollama run $MODEL_NAME "Explain anticipatory bail."
    Write-Host "✅ Model is working properly!" -ForegroundColor Green
    Write-Host "Smoke test output snippet: $($testResult.Substring(0, [math]::Min($testResult.Length, 100)))..." -ForegroundColor Gray
} catch {
    Write-Host "❌ Smoke test failed." -ForegroundColor Red
}

Write-Host "`nSetup complete! You can now start the LexVerify backend." -ForegroundColor Green
