#!/usr/bin/env python3
"""
Local AI Code Summarizer - Optimized for RTX 3050Ti
Replacement for OpenRouter API calls
"""

import ollama
import os
import argparse
import time
from pathlib import Path
import psutil
import GPUtil
from tqdm import tqdm

class LocalLLMSummarizer:
    def __init__(self, model_name="codellama:7b-instruct-q4_K_M"):
        self.model_name = model_name
        print(f"🚀 Initializing {model_name} on RTX 3050Ti...")
        
        # Warm up the model
        self.warm_up_model()
    
    def warm_up_model(self):
        """Pre-load model to GPU for faster responses"""
        try:
            ollama.generate(
                model=self.model_name,
                prompt="Hello",
                options={'num_ctx': 2048}
            )
            print("✅ Model loaded and ready!")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise
    
    def monitor_gpu(self):
        """Monitor GPU usage"""
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                return {
                    'memory_used': gpu.memoryUsed,
                    'memory_total': gpu.memoryTotal,
                    'memory_percent': (gpu.memoryUsed / gpu.memoryTotal) * 100,
                    'load': gpu.load * 100,
                    'temp': gpu.temperature
                }
        except:
            return None
    
    def summarize_code(self, code_content, file_path="", max_tokens=4000):
        """Replace your OpenRouter API call with this function"""
        
        # Check if content needs chunking
        if len(code_content) > max_tokens:
            return self.summarize_large_code(code_content, file_path)
        
        prompt = f"""Analyze this code and provide a comprehensive summary:

File: {file_path}
Code:
{code_content}

Provide:
1. **Purpose**: Main functionality
2. **Key Components**: Important classes/functions  
3. **Technologies**: Languages and frameworks used
4. **Architecture**: Design patterns
5. **Complexity**: Low/Medium/High
6. **Dependencies**: Required libraries

Keep it concise but thorough."""

        try:
            # Monitor GPU before generation
            gpu_info = self.monitor_gpu()
            if gpu_info:
                print(f"🔧 GPU: {gpu_info['memory_percent']:.1f}% VRAM, {gpu_info['temp']}°C")
            
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    'temperature': 0.2,
                    'top_p': 0.9,
                    'num_ctx': 4096,
                    'num_gpu': 1,  # Use your RTX 3050Ti
                    'num_thread': 6  # Good for your system
                }
            )
            
            return response['response']
            
        except Exception as e:
            print(f"❌ Error generating summary: {e}")
            raise
    
    def summarize_large_code(self, code_content, file_path="", chunk_size=3000):
        """Handle large files by chunking"""
        chunks = [code_content[i:i+chunk_size] 
                 for i in range(0, len(code_content), chunk_size)]
        
        print(f"📄 Processing {file_path} in {len(chunks)} chunks...")
        
        chunk_summaries = []
        for i, chunk in enumerate(chunks, 1):
            print(f"Processing chunk {i}/{len(chunks)}")
            
            summary = ollama.generate(
                model=self.model_name,
                prompt=f"Summarize this code section from {file_path}:\n\n{chunk}",
                options={'num_gpu': 1, 'temperature': 0.2}
            )
            
            chunk_summaries.append(summary['response'])
            time.sleep(0.5)  # Brief pause between chunks
        
        # Create final summary
        final_prompt = f"""Create a comprehensive summary from these sections of {file_path}:

""" + "\n\n".join([f"Section {i+1}: {summary}" 
                   for i, summary in enumerate(chunk_summaries)])
        
        final_response = ollama.generate(
            model=self.model_name,
            prompt=final_prompt,
            options={'num_gpu': 1}
        )
        
        return final_response['response']
    
    def batch_summarize(self, file_paths, output_file=None):
        """Summarize multiple files efficiently"""
        results = {}
        
        for i, file_path in enumerate(file_paths, 1):
            print(f"\n📝 Processing {i}/{len(file_paths)}: {file_path}")
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                if content.strip():
                    summary = self.summarize_code(content, str(file_path))
                    results[str(file_path)] = summary
                
                # Show progress
                gpu_info = self.monitor_gpu()
                if gpu_info:
                    print(f"GPU Status: {gpu_info['memory_percent']:.1f}% VRAM used")
                
            except Exception as e:
                print(f"❌ Error processing {file_path}: {e}")
                results[str(file_path)] = f"Error: {str(e)}"
        
        # Save results
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                for file_path, summary in results.items():
                    f.write(f"# {file_path}\n\n{summary}\n\n---\n\n")
            print(f"💾 Results saved to {output_file}")
        
        return results

def main():
    parser = argparse.ArgumentParser(description='Local AI Code Summarizer')
    parser.add_argument('path', help='File or directory path')
    parser.add_argument('--model', '-m', default='codellama:7b-instruct-q4_K_M',
                       help='Ollama model to use')
    parser.add_argument('--output', '-o', help='Output file')
    parser.add_argument('--recursive', '-r', action='store_true')
    
    args = parser.parse_args()
    
    # Initialize summarizer
    summarizer = LocalLLMSummarizer(args.model)
    
    path = Path(args.path)
    
    if path.is_file():
        # Single file
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        summary = summarizer.summarize_code(content, str(path))
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(summary)
            print(f"💾 Summary saved to {args.output}")
        else:
            print(f"\n{'='*50}")
            print(f"SUMMARY: {path.name}")
            print('='*50)
            print(summary)
    
    elif path.is_dir():
        # Directory processing
        extensions = {'.py', '.java', '.js', '.cpp', '.c', '.h', '.cs', '.go', '.rs', '.php', '.ts', '.jsx', '.tsx'}
        
        files = []
        if args.recursive:
            for ext in extensions:
                files.extend(path.rglob(f"*{ext}"))
        else:
            for ext in extensions:
                files.extend(path.glob(f"*{ext}"))
        
        if files:
            print(f"🔍 Found {len(files)} code files")
            results = summarizer.batch_summarize(files, args.output)
            
            if not args.output:
                for file_path, summary in results.items():
                    print(f"\n{'='*50}")
                    print(f"FILE: {file_path}")
                    print('='*50)
                    print(summary)
        else:
            print("❌ No code files found")

if __name__ == "__main__":
    main()
