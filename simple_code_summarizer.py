#!/usr/bin/env python3
"""
Simple AI Code Summarizer - Works without GPUtil
Optimized for your RTX 3050Ti with Ollama
"""

import ollama
import os
import argparse
import time
from pathlib import Path

class SimpleCodeSummarizer:
    def __init__(self, model_name="codellama:7b-instruct-q4_K_M"):
        self.model_name = model_name
        print(f"🚀 Initializing {model_name}...")
        
        # Test that the model works
        try:
            response = ollama.generate(
                model=self.model_name,
                prompt="Hello",
                options={'num_ctx': 512}
            )
            print("✅ Model loaded and ready!")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise
    
    def summarize_code(self, code_content, file_path=""):
        """Main function to summarize code"""
        
        # For very large files, chunk them
        if len(code_content) > 4000:
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
5. **Dependencies**: Required libraries

Keep it concise but thorough."""

        try:
            print(f"🔄 Analyzing {file_path or 'code'}...")
            
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    'temperature': 0.2,
                    'top_p': 0.9,
                    'num_ctx': 4096,
                }
            )
            
            return response['response']
            
        except Exception as e:
            print(f"❌ Error generating summary: {e}")
            raise
    
    def summarize_large_code(self, code_content, file_path="", chunk_size=3000):
        """Handle large files by splitting them"""
        chunks = [code_content[i:i+chunk_size] 
                 for i in range(0, len(code_content), chunk_size)]
        
        print(f"📄 Processing large file {file_path} in {len(chunks)} chunks...")
        
        chunk_summaries = []
        for i, chunk in enumerate(chunks, 1):
            print(f"  Processing chunk {i}/{len(chunks)}")
            
            response = ollama.generate(
                model=self.model_name,
                prompt=f"Summarize this code section from {file_path}:\n\n{chunk}",
                options={'temperature': 0.2, 'num_ctx': 4096}
            )
            
            chunk_summaries.append(response['response'])
            time.sleep(0.5)  # Brief pause
        
        # Create final comprehensive summary
        print("  Creating final summary...")
        final_prompt = f"""Create a comprehensive summary from these sections of {file_path}:

""" + "\n\n".join([f"Section {i+1}: {summary}" 
                   for i, summary in enumerate(chunk_summaries)])
        
        final_response = ollama.generate(
            model=self.model_name,
            prompt=final_prompt,
            options={'temperature': 0.2, 'num_ctx': 4096}
        )
        
        return final_response['response']

def main():
    parser = argparse.ArgumentParser(description='Simple AI Code Summarizer')
    parser.add_argument('path', help='File or directory path')
    parser.add_argument('--model', '-m', default='codellama:7b-instruct-q4_K_M',
                       help='Ollama model to use')
    parser.add_argument('--output', '-o', help='Output file')
    parser.add_argument('--recursive', '-r', action='store_true')
    
    args = parser.parse_args()
    
    # Initialize summarizer
    summarizer = SimpleCodeSummarizer(args.model)
    
    path = Path(args.path)
    
    if not path.exists():
        print(f"❌ Path {path} does not exist")
        return
    
    if path.is_file():
        # Single file
        print(f"📝 Processing file: {path}")
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        summary = summarizer.summarize_code(content, str(path))
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(f"# Summary of {path}\n\n{summary}")
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
        
        if not files:
            print("❌ No code files found")
            return
        
        print(f"🔍 Found {len(files)} code files")
        
        results = []
        for i, file_path in enumerate(files, 1):
            print(f"\n📝 Processing {i}/{len(files)}: {file_path.name}")
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                if content.strip():
                    summary = summarizer.summarize_code(content, str(file_path))
                    results.append(f"## {file_path.name}\n\n{summary}\n")
                
            except Exception as e:
                print(f"❌ Error processing {file_path}: {e}")
                results.append(f"## {file_path.name}\n\nError: {str(e)}\n")
        
        # Output all results
        final_output = "\n".join(results)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(final_output)
            print(f"💾 All summaries saved to {args.output}")
        else:
            print(f"\n{'='*60}")
            print("PROJECT SUMMARY")
            print('='*60)
            print(final_output)

if __name__ == "__main__":
    main()

