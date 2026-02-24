const express = require('express');
const cors = require('cors');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// API endpoint to analyze folder
app.post('/api/analyze', (req, res) => {
    const { folderPath, model } = req.body;

    if (!folderPath) {
        return res.status(400).json({ error: 'Folder path is required' });
    }

    if (!fs.existsSync(folderPath)) {
        return res.status(400).json({ error: 'Folder not found' });
    }

    const stats = fs.statSync(folderPath);
    if (!stats.isDirectory()) {
        return res.status(400).json({ error: 'Path is not a directory' });
    }

    // Set up progress tracking
    let progressData = [];
    let totalFiles = 0;
    let processedFiles = 0;

    // Spawn Python process to run the tokenizer.
    // folderPath and model are passed via environment variables (not string
    // interpolation) to prevent code injection.
    const pythonProcess = spawn('python3', [
        '-c',
        `
import sys
import json
import os
from pathlib import Path
sys.path.insert(0, '${path.join(__dirname, 'src')}')
from folder_tokenizer.tokenizer import FolderTokenizer

model_name = os.environ['FT_MODEL']
folder_path = os.environ['FT_FOLDER_PATH']

tokenizer = FolderTokenizer(model_name=model_name)

def progress_callback(current, total, file_result):
    print(json.dumps({
        'type': 'progress',
        'current': current,
        'total': total,
        'file': file_result.path,
        'file_name': Path(file_result.path).name
    }), flush=True)

result = tokenizer.process_folder(folder_path, progress_callback=progress_callback)

# Output final result
print(json.dumps({
    'type': 'result',
    'total_tokens': result.total_tokens,
    'total_chars': result.total_chars,
    'successful_files': result.successful_files,
    'failed_files': result.failed_files,
    'by_type': result.by_type,
    'file_results': [
        {
            'path': fr.path,
            'file_type': fr.file_type,
            'tokens': fr.tokens,
            'chars': fr.chars,
            'success': fr.success,
            'error': fr.error,
            'source_archive': fr.source_archive
        }
        for fr in result.file_results
    ]
}), flush=True)
        `.trim(),
    ], {
        env: {
            ...process.env,
            FT_MODEL: model || 'gpt2',
            FT_FOLDER_PATH: folderPath,
        },
    });

    let outputBuffer = '';
    let resultSent = false;

    pythonProcess.stdout.on('data', (data) => {
        outputBuffer += data.toString();
        const lines = outputBuffer.split('\n');
        outputBuffer = lines.pop(); // Keep incomplete line in buffer

        lines.forEach(line => {
            if (line.trim()) {
                try {
                    const jsonData = JSON.parse(line);
                    if (jsonData.type === 'progress') {
                        // Send progress updates (could be used for SSE in future)
                        console.log(`Progress: ${jsonData.current}/${jsonData.total} - ${jsonData.file_name}`);
                    } else if (jsonData.type === 'result') {
                        if (!resultSent && !res.headersSent) {
                            resultSent = true;
                            res.json(jsonData);
                        }
                    }
                } catch (e) {
                    console.error('Failed to parse JSON:', line);
                }
            }
        });
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`Python Error: ${data}`);
    });

    pythonProcess.on('close', (code) => {
        // Wait for any buffered stdout (result line) to be processed before sending
        // an error from here; otherwise we send first and then stdout sends → ERR_HTTP_HEADERS_SENT
        const exitCode = code;
        setTimeout(() => {
            if (resultSent || res.headersSent) return;
            resultSent = true;
            if (exitCode !== 0) {
                res.status(500).json({ error: 'Python process failed' });
            } else {
                res.status(500).json({ error: 'No result received from Python process' });
            }
        }, 150);
    });

    pythonProcess.on('error', (error) => {
        if (!resultSent && !res.headersSent) {
            resultSent = true;
            res.status(500).json({ error: error.message });
        }
    });
});

// API endpoint to open native folder picker
app.get('/api/browse', (req, res) => {
    const { exec } = require('child_process');
    
    // Use osascript to open native folder picker on macOS
    const script = `
        osascript -e 'POSIX path of (choose folder with prompt "Select a folder to analyze")'
    `;
    
    exec(script.trim(), (error, stdout, stderr) => {
        if (error) {
            // User cancelled or error occurred
            return res.json({ path: null, cancelled: true });
        }
        
        const folderPath = stdout.trim();
        // Remove trailing slash if present
        const cleanPath = folderPath.endsWith('/') ? folderPath.slice(0, -1) : folderPath;
        res.json({ path: cleanPath, cancelled: false });
    });
});

// API endpoint to get list of popular models
app.get('/api/models', (req, res) => {
    res.json({
        models: [
            // OpenAI-style
            { name: 'gpt2', label: 'GPT-2 (OpenAI)' },
            { name: 'Xenova/gpt-4o', label: 'GPT-4o (OpenAI)' },
            { name: 'Xenova/claude-tokenizer', label: 'Claude (Anthropic)' },
            // Meta LLaMA
            { name: 'meta-llama/Llama-2-7b-hf', label: 'LLaMA 2 (Meta)' },
            { name: 'meta-llama/Meta-Llama-3-8B', label: 'LLaMA 3 (Meta)' },
            { name: 'meta-llama/Llama-3.2-1B', label: 'LLaMA 3.2 (Meta)' },
            // Mistral
            { name: 'mistralai/Mistral-7B-v0.1', label: 'Mistral 7B' },
            { name: 'mistralai/Mixtral-8x7B-v0.1', label: 'Mixtral 8x7B' },
            // Google (Gemini/Gemma use same tokenizer)
            { name: 'google/gemma-2-2b', label: 'Gemma 2 2B (Google)' },
            { name: 'google/gemma-2-9b', label: 'Gemma 2 9B (Google)' },
            { name: 'google/gemma-2-27b', label: 'Gemma 2 27B (Google)' },
            // Other popular models
            { name: 'Qwen/Qwen2.5-7B', label: 'Qwen 2.5 (Alibaba)' },
            { name: 'microsoft/phi-2', label: 'Phi-2 (Microsoft)' },
            { name: 'deepseek-ai/DeepSeek-V2-Lite', label: 'DeepSeek V2' },
            { name: 'tiiuae/falcon-7b', label: 'Falcon 7B (TII)' },
            // Encoder models
            { name: 'bert-base-uncased', label: 'BERT Base' },
            { name: 'sentence-transformers/all-MiniLM-L6-v2', label: 'MiniLM (Embeddings)' }
        ]
    });
});

app.listen(PORT, () => {
    console.log(`🚀 Folder Tokenizer server running at http://localhost:${PORT}`);
    console.log(`📊 Open your browser to start analyzing folders`);
});
