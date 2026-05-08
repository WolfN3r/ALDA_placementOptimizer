#!/usr/bin/env python3
"""
Universal n8n JSON Handler
Handles JSON communication between n8n and external Python scripts with safe encoding
Auto-unwraps {"batch": [...]} structure and ensures UTF-8 safety
"""

import json
import subprocess
import sys
import gc
import os


class N8nJsonHandler:
    """Universal handler for n8n JSON communication with safe encoding"""

    def __init__(self):
        self.input_data = None
        self.output_data = None
        self._stdout_fd = None  # Saved real stdout fd, set by _protect_stdout()

    def load_from_n8n(self):
        """
        Safely load JSON from n8n stdin with proper encoding handling
        Automatically unwraps {"batch": [...]} structure if present
        Returns: True if successful, False otherwise
        """
        try:
            # Safe encoding handling - prevents ASCII character issues
            input_bytes = sys.stdin.buffer.read()
            input_text = input_bytes.decode('utf-8', errors='strict')
            self.input_data = json.loads(input_text)
            
            # Auto-unwrap {"batch": [...]} structure from n8n Python nodes
            if isinstance(self.input_data, dict) and len(self.input_data) == 1 and 'batch' in self.input_data:
                if isinstance(self.input_data['batch'], list):
                    self.input_data = self.input_data['batch']
            
            return True
        except Exception as e:
            self._output_error(f"Failed to load JSON from n8n: {str(e)}")
            return False

    def load_from_file(self, filename):
        """
        Load JSON from file (for standalone testing)
        Automatically unwraps {"batch": [...]} structure if present
        Args:
            filename (str): Path to JSON file
        Returns: True if successful, False otherwise
        """
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.input_data = json.load(f)
            
            # Auto-unwrap {"batch": [...]} structure
            if isinstance(self.input_data, dict) and len(self.input_data) == 1 and 'batch' in self.input_data:
                if isinstance(self.input_data['batch'], list):
                    self.input_data = self.input_data['batch']
            
            return True
        except Exception as e:
            self._output_error(f"Failed to load JSON from file {filename}: {str(e)}")
            return False

    def get_data(self):
        """
        Get the loaded data for processing
        Returns: Loaded JSON data or None
        """
        return self.input_data

    def set_output(self, data):
        """
        Set the output data to be sent back to n8n
        Args:
            data: Any JSON-serializable data structure
        """
        self.output_data = data

    def _sanitize_for_utf8(self, obj):
        """
        Recursively sanitize data to ensure UTF-8 compatibility
        Removes or replaces non-UTF-8 characters
        Args:
            obj: Any JSON-serializable object
        Returns: Sanitized object safe for UTF-8 encoding
        """
        if isinstance(obj, str):
            # Encode to UTF-8 and decode, replacing errors
            return obj.encode('utf-8', errors='replace').decode('utf-8')
        elif isinstance(obj, dict):
            return {self._sanitize_for_utf8(k): self._sanitize_for_utf8(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._sanitize_for_utf8(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(self._sanitize_for_utf8(item) for item in obj)
        else:
            return obj

    def _protect_stdout(self):
        """
        Redirect stdout to /dev/null for the entire processing duration.

        Called once, immediately after input is loaded.  Any write to
        sys.stdout or fd 1 (from Python code, C extensions, numpy, matplotlib,
        imageio, ffmpeg, …) goes to /dev/null instead of the pipe that n8n reads.
        The real stdout fd is saved in self._stdout_fd and used exclusively by
        _write_json_to_stdout() at the very end.

        /dev/null is used instead of stderr so that this is safe regardless of
        how the subprocess was spawned: if the caller inherited stderr from n8n's
        output pipe (which n8n-nodes-python reads as JSON), routing noise there
        would corrupt the JSON.  /dev/null is always harmless.
        """
        try:
            sys.stdout.flush()
            self._stdout_fd = os.dup(1)                  # save real stdout fd
            _devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(_devnull, 1)                         # fd 1 → /dev/null
            os.close(_devnull)
            sys.stdout = open(os.devnull, 'w')           # Python print() → /dev/null
        except OSError:
            self._stdout_fd = None                       # fall back to plain print()

    def _write_json_to_stdout(self, text):
        """
        Write a JSON string directly to the saved real stdout fd.

        Uses os.write() which bypasses Python's I/O stack entirely, so no
        sys.stdout manipulation (including the one done by _protect_stdout)
        can intercept or delay the output.
        """
        data = (text + '\n').encode('ascii')
        if self._stdout_fd is not None:
            try:
                os.write(self._stdout_fd, data)
            except OSError:
                pass  # best-effort; process is about to exit anyway
        else:
            try:
                sys.stdout.write(text + '\n')
                sys.stdout.flush()
            except Exception:
                pass

    def output_to_n8n(self):
        """
        Safely output JSON to n8n stdout with UTF-8 sanitization
        """
        if self.output_data is not None:
            try:
                # Sanitize data to ensure UTF-8 safety
                safe_output = self._sanitize_for_utf8(self.output_data)

                # Safe JSON output with UTF-8 encoding
                output_text = json.dumps(safe_output, ensure_ascii=True, separators=(',', ':'))
                self._write_json_to_stdout(output_text)
            except Exception as e:
                self._output_error(f"Failed to serialize output: {str(e)}")
        else:
            self._output_error("No output data set")

    def _output_error(self, error_message):
        """
        Output error in n8n-compatible format
        Args:
            error_message (str): Error description
        """
        error_response = {
            "error": error_message,
            "success": False,
            "data": None
        }
        try:
            self._write_json_to_stdout(json.dumps(error_response, ensure_ascii=True))
        except:
            self._write_json_to_stdout('{"error":"Critical JSON serialization error","success":false}')


def create_n8n_processor(user_processor_function):
    """
    Universal function that wraps user processing logic for n8n

    Args:
        user_processor_function: Function that takes JSON data and returns processed JSON
                                Signature: user_function(json_data) -> processed_json_data

    Returns: Function ready for n8n execution
    """

    def n8n_wrapper():
        handler = N8nJsonHandler()

        # Load input from n8n
        if not handler.load_from_n8n():
            return  # Error already output by handler

        # Protect stdout for the entire processing duration.
        # Redirects fd 1 and sys.stdout → stderr so that any output from
        # Python libraries (numpy, matplotlib, imageio, ffmpeg, …) goes to
        # stderr (Docker logs) instead of the pipe n8n reads as JSON.
        # The real stdout fd is saved and used exclusively by output_to_n8n().
        handler._protect_stdout()

        # Get data for processing
        input_data = handler.get_data()

        try:
            # Call user's processing function
            processed_data = user_processor_function(input_data)

            # Set output and send to n8n
            handler.set_output(processed_data)
            handler.output_to_n8n()

            # Cleanup
            del input_data, processed_data
            gc.collect()

        except Exception as e:
            handler._output_error(f"Processing error: {str(e)}")

    return n8n_wrapper


def create_file_processor(user_processor_function):
    """
    Universal function that wraps user processing logic for file-based testing

    Args:
        user_processor_function: Function that takes JSON data and returns processed JSON

    Returns: Function that can process files
    """

    def file_wrapper(input_filename, output_filename=None):
        handler = N8nJsonHandler()

        # Load input from file
        if not handler.load_from_file(input_filename):
            return False

        # Get data for processing
        input_data = handler.get_data()

        try:
            # Call user's processing function
            processed_data = user_processor_function(input_data)

            # Output to file or stdout
            if output_filename:
                with open(output_filename, 'w', encoding='utf-8') as f:
                    json.dump(processed_data, f, ensure_ascii=False, indent=2)
                print(f"Output saved to: {output_filename}")
            else:
                handler.set_output(processed_data)
                handler.output_to_n8n()

            # Cleanup
            del input_data, processed_data
            gc.collect()

            return True

        except Exception as e:
            print(f"Processing error: {str(e)}", file=sys.stderr)
            return False

    return file_wrapper


def run_processor_from_file(filename, user_processor_function):
    """
    Convenience function to run processor with JSON file input

    Args:
        filename (str): Path to input JSON file
        user_processor_function: User's processing function

    Returns: Processed data or None if error
    """
    handler = N8nJsonHandler()

    if not handler.load_from_file(filename):
        return None

    try:
        input_data = handler.get_data()
        result = user_processor_function(input_data)

        # Cleanup
        del input_data
        gc.collect()

        return result

    except Exception as e:
        print(f"Processing error: {str(e)}", file=sys.stderr)
        return None


# Example usage and testing
def example_processor(json_data):
    """
    Example processing function - replace with your logic

    Args:
        json_data: Input JSON data from n8n or file

    Returns: Processed JSON data
    """
    if isinstance(json_data, dict):
        # Add processing metadata
        json_data['processed'] = True
        json_data['example_processing'] = 'completed'

        # Example: count items if present
        if 'items' in json_data and isinstance(json_data['items'], list):
            json_data['item_count'] = len(json_data['items'])
            json_data['processing_summary'] = f"Processed {len(json_data['items'])} items"

    return json_data


def run_n8n_script(script_path, items):
    """
    Run a standalone Python script as a subprocess, passing items via stdin
    and reading the JSON result from stdout.

    Inner subprocess stderr is captured and silenced — NOT forwarded to the
    calling process's stderr.  The calling process runs inside naskio's
    script.template.py, which writes its own result to stderr; naskio then
    reads that channel with JSON.parse().  Forwarding any noise there causes:
        SyntaxError: Unexpected token r in JSON at position 1
    See n8n_json_handler_errorLog.md for the full diagnosis.
    """
    if isinstance(items, list) and len(items) == 1:
        payload = items[0]
    elif isinstance(items, list):
        payload = {"batch": items}
    else:
        payload = items

    proc = subprocess.Popen(
        ['python3', script_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,  # captured but NOT forwarded to outer stderr
        text=True,
    )
    json_data = json.dumps(payload)
    stdout, _stderr = proc.communicate(json_data)
    # _stderr intentionally discarded: forwarding it would contaminate the
    # outer stderr channel that naskio reads as JSON.
    del json_data, payload
    gc.collect()

    response = json.loads(stdout)
    return response if isinstance(response, list) else [response]


if __name__ == "__main__":
    # For n8n integration - create processor and run
    n8n_processor = create_n8n_processor(example_processor)
    n8n_processor()