# auth.py
import os
import sys
from pathlib import Path
import click
from zettl.config import AUTH_URL
import requests

class ZettlAuth:
    def __init__(self):
        self.config_dir = Path.home() / '.zettl'
        self.config_file = self.config_dir / 'config'
        self.config_dir.mkdir(exist_ok=True)

    def get_api_key(self):
        """Get API key from config file."""
        # Check config file
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    for line in f:
                        if line.startswith('api_key='):
                            return line.split('=', 1)[1].strip()
            except Exception:
                pass

        return None

    def set_api_key(self, api_key):
        """Save API key to config file."""
        try:
            # Read existing config
            config_lines = []
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config_lines = [line for line in f if not line.startswith('api_key=')]

            # Add new API key
            config_lines.append(f'api_key={api_key}\n')

            # Write config
            with open(self.config_file, 'w') as f:
                f.writelines(config_lines)

            # Set restrictive permissions
            os.chmod(self.config_file, 0o600)

            # Clear auth cache when setting new key
            cache_file = self.config_dir / '.auth_cache'
            if cache_file.exists():
                try:
                    cache_file.unlink()
                except:
                    pass

            return True
        except Exception as e:
            click.echo(f"Error saving API key: {e}", err=True)
            return False

    def test_api_key(self, api_key=None):
        """Test if CLI token is valid."""
        if not api_key:
            api_key = self.get_api_key()

        if not api_key:
            return False

        try:
            # Use the new CLI token validation endpoint
            # AUTH_URL already includes /api/auth, so just add the endpoint
            response = requests.post(f'{AUTH_URL}/validate-cli-token',
                                   headers={'X-API-Key': api_key},
                                   timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def require_auth(self):
        """Ensure user is authenticated, prompt for setup if not."""
        api_key = self.get_api_key()

        if not api_key:
            click.echo("Authentication required.")
            click.echo("Please generate an API key using the web interface at:")
            click.echo("http://localhost:8080 (or your Zettl web URL)")
            click.echo("")
            click.echo("Then run: zettl auth setup")
            sys.exit(1)

        # Check cached validation status first (valid for 24 hours)
        cache_file = self.config_dir / '.auth_cache'
        if cache_file.exists():
            try:
                import time
                with open(cache_file, 'r') as f:
                    cached_time = float(f.read().strip())
                    # If validated within last 24 hours, skip validation
                    if time.time() - cached_time < 86400:  # 24 hours
                        return api_key
            except:
                pass

        # Only validate if cache is expired or missing
        if not self.test_api_key(api_key):
            click.echo("Authentication required.")
            click.echo("API key is invalid or expired.")
            click.echo("Please generate a new API key using the web interface at:")
            click.echo("http://localhost:8080 (or your Zettl web URL)")
            click.echo("")
            click.echo("Then run: zettl auth setup")
            sys.exit(1)

        # Cache successful validation
        try:
            import time
            with open(cache_file, 'w') as f:
                f.write(str(time.time()))
            os.chmod(cache_file, 0o600)
        except:
            pass  # Continue even if caching fails

        return api_key

# Global auth instance
auth = ZettlAuth()