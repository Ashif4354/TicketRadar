# scripts/set_admin.py
import sys
import os
import firebase_admin
from firebase_admin import credentials, auth

# Get project root
scripts_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(scripts_dir, ".."))
env_path = os.path.join(root_dir, "src", "Backend", ".env")

# Parse .env file manually to load variables into environment
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                val = val.strip()
                # Strip quotes if present
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                os.environ[key.strip()] = val
else:
    print(f"Warning: .env configuration file not found at {env_path}")

# Initialize Firebase using environment variables
if not firebase_admin._apps:
    try:
        cred_dict = {
            "type": os.getenv("FIREBASE_TYPE", ""),
            "project_id": os.getenv("FIREBASE_PROJECT_ID", ""),
            "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID", ""),
            "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
            "client_email": os.getenv("FIREBASE_CLIENT_EMAIL", ""),
            "client_id": os.getenv("FIREBASE_CLIENT_ID", ""),
            "auth_uri": os.getenv("FIREBASE_AUTH_URI", ""),
            "token_uri": os.getenv("FIREBASE_TOKEN_URI", ""),
            "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL", ""),
            "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL", ""),
            "universe_domain": os.getenv("FIREBASE_UNIVERSE_DOMAIN", "googleapis.com")
        }
        
        if cred_dict["project_id"] and cred_dict["private_key"]:
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
        else:
            print("Error: Firebase environment configuration is incomplete in .env.")
            sys.exit(1)
    except Exception as e:
        print(f"Failed to initialize Firebase Admin SDK: {e}")
        sys.exit(1)

def set_admin(email):
    try:
        user = auth.get_user_by_email(email)
        claims = user.custom_claims or {}
        claims["role"] = "admin"
        claims["authorized"] = True
        claims["blocked"] = False
        
        auth.set_custom_user_claims(user.uid, claims)
        print(f"Successfully promoted {email} to ADMIN with full authorizations.")
        print(f"UID: {user.uid}")
        print(f"New Custom Claims: {claims}")
    except Exception as e:
        print(f"Error setting admin: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python set_admin.py <user_email>")
        sys.exit(1)
    
    email = sys.argv[1].strip()
    set_admin(email)
