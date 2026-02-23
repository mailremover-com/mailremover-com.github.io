"""
R2 Vault — BYOS (Bring Your Own Storage) for MailRemover
=========================================================
Stores a copy of every trashed email in the user's own Cloudflare R2 bucket.
Users own their data. MailRemover is just the pipe.
"""

import re
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from datetime import datetime


def get_r2_client(account_id, access_key_id, secret_access_key):
    return boto3.client(
        's3',
        endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        config=Config(signature_version='s3v4'),
        region_name='auto'
    )


def test_connection(account_id, access_key_id, secret_access_key, bucket_name):
    """Test R2 credentials by checking bucket access."""
    try:
        client = get_r2_client(account_id, access_key_id, secret_access_key)
        client.head_bucket(Bucket=bucket_name)
        return True, "Connected"
    except ClientError as e:
        code = e.response['Error']['Code']
        if code in ('403', 'AccessDenied'):
            return False, "Access denied — check your Access Key and Secret"
        if code in ('404', 'NoSuchBucket'):
            return False, "Bucket not found — check your bucket name"
        return False, f"Error {code}: {e.response['Error']['Message']}"
    except Exception as e:
        return False, str(e)


def backup_email(account_id, access_key_id, secret_access_key, bucket_name,
                 user_email, msg_id, subject, sender, raw_eml_bytes):
    """
    Store a raw EML file in the user's R2 bucket.
    Path: {user_email}/{year}/{month}/{timestamp}_{msg_id}_{safe_subject}.eml
    """
    try:
        client = get_r2_client(account_id, access_key_id, secret_access_key)
        now = datetime.utcnow()
        safe_subject = re.sub(r'[^\w\s-]', '', subject or 'no-subject').strip()[:40]
        key = (f"{user_email}/{now.year}/{now.month:02d}/"
               f"{now.strftime('%Y%m%d_%H%M%S')}_{msg_id}_{safe_subject}.eml")

        client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=raw_eml_bytes,
            ContentType='message/rfc822',
            Metadata={
                'msg-id': msg_id[:256],
                'subject': (subject or '')[:256],
                'sender': (sender or '')[:256],
                'archived-at': now.isoformat()
            }
        )
        return True, key
    except Exception as e:
        return False, str(e)


def list_vault(account_id, access_key_id, secret_access_key, bucket_name,
               user_email, search=None, continuation_token=None):
    """List emails in the user's vault, with optional search."""
    try:
        client = get_r2_client(account_id, access_key_id, secret_access_key)
        prefix = f"{user_email}/"

        kwargs = {'Bucket': bucket_name, 'Prefix': prefix, 'MaxKeys': 100}
        if continuation_token:
            kwargs['ContinuationToken'] = continuation_token

        response = client.list_objects_v2(**kwargs)

        items = []
        for obj in response.get('Contents', []):
            key = obj['Key']
            filename = key.split('/')[-1]

            # Get metadata
            try:
                head = client.head_object(Bucket=bucket_name, Key=key)
                meta = head.get('Metadata', {})
                subject = meta.get('subject', filename)
                sender = meta.get('sender', '')
                archived_at = meta.get('archived-at', '')
            except Exception:
                subject = filename
                sender = ''
                archived_at = ''

            # Apply search filter
            if search:
                s = search.lower()
                if s not in subject.lower() and s not in sender.lower() and s not in filename.lower():
                    continue

            items.append({
                'key': key,
                'filename': filename,
                'subject': subject,
                'sender': sender,
                'archived_at': archived_at,
                'size_kb': round(obj['Size'] / 1024, 1),
                'last_modified': obj['LastModified'].isoformat()
            })

        # Sort newest first
        items.sort(key=lambda x: x['last_modified'], reverse=True)

        return {
            'ok': True,
            'items': items,
            'count': len(items),
            'truncated': response.get('IsTruncated', False),
            'next_token': response.get('NextContinuationToken')
        }
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def download_email(account_id, access_key_id, secret_access_key, bucket_name, key):
    """Download a single EML file from R2, returns bytes."""
    try:
        client = get_r2_client(account_id, access_key_id, secret_access_key)
        response = client.get_object(Bucket=bucket_name, Key=key)
        return True, response['Body'].read()
    except Exception as e:
        return False, str(e)
