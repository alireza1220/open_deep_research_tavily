"""Utilities for managing ngrok tunnels."""

import sys
from typing import Optional



def setup_ngrok(port: int) -> Optional[str]:
    """Set up ngrok tunnel and return public URL."""
    try:
        from pyngrok import ngrok
    except ImportError:
        print(
            "Error: pyngrok is not installed. Install it with: pip install pyngrok",
            file=sys.stderr,
        )
        sys.exit(1)
    
    try:
        # Create ngrok tunnel
        public_url = ngrok.connect(port)
        print(f"\n{'='*60}")
        print(f"ngrok tunnel created successfully!")
        print(f"Public URL: {public_url}")
        print(f"Local URL: http://localhost:{port}")
        print(f"{'='*60}\n")
        return str(public_url)
    except Exception as e:
        print(f"Error creating ngrok tunnel: {e}", file=sys.stderr)
        sys.exit(1)




def cleanup_ngrok():
    """Clean up ngrok tunnels."""
    try:
        from pyngrok import ngrok
        ngrok.kill()
    except Exception:
        pass  # Ignore errors during cleanup
