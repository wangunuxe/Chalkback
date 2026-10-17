"""给 Hub 生成自签证书 key.pem / cert.pem（本地开发和 Docker 联调用 HTTPS）。

写在本文件所在的 hub/ 目录：宿主机（make hub）和 Docker（/app/hub）都适用。
已有证书就不重新生成；加 --force 强制重新生成。公网部署请换成正式证书（见 docs/ADMIN.md）。
"""
from __future__ import annotations
import datetime
import ipaddress
import sys
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

def generate(force: bool = False):
    out_dir = Path(__file__).resolve().parent
    if not force and (out_dir / "key.pem").exists() and (out_dir / "cert.pem").exists():
        print(f"Hub SSL certificates already exist in {out_dir}")
        return
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, "localhost")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
        .sign(key, hashes.SHA256())
    )
    (out_dir / "key.pem").write_bytes(
        key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption())
    )
    (out_dir / "cert.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    print("SSL certificates generated successfully.")

if __name__ == "__main__":
    generate(force="--force" in sys.argv)
