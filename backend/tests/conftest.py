"""Configure test-only settings before application imports; never use the dev DB."""
import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite://"
os.environ["SECRET_KEY"] = "isolated-auth-tests-only-secret-key-123456"
os.environ["DEBUG"] = "false"
