import os
import json
import urllib.request
import boto3

EBS_GB_MONTHLY_COST = 0.10
EIP_MONTHLY_COST = 3.65

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    
    volumes_response = ec2.describe_volumes(
        Filters=[{'Name': 'status', 'Values': ['available']}]
    )
    unattached_volumes = volumes_response.get('Volumes', [])
    total_ebs_size_gb = sum(vol.get('Size', 0) for vol in unattached_volumes)
    ebs_estimated_cost = total_ebs_size_gb * EBS_GB_MONTHLY_COST
    
    addresses_response = ec2.describe_addresses()
    unassociated_eips = [
        addr for addr in addresses_response.get('Addresses', [])
        if 'AssociationId' not in addr
    ]
    eip_estimated_cost = len(unassociated_eips) * EIP_MONTHLY_COST
    
    total_idle_spend = ebs_estimated_cost + eip_estimated_cost
    
    payload = {
        "summary": "AWS FinOps Janitor Idle Resource Report",
        "unattached_ebs_count": len(unattached_volumes),
        "unattached_ebs_total_gb": total_ebs_size_gb,
        "ebs_estimated_monthly_spend": ebs_estimated_cost,
        "unassociated_eip_count": len(unassociated_eips),
        "eip_estimated_monthly_spend": eip_estimated_cost,
        "total_estimated_idle_monthly_spend": total_idle_spend
    }
    
    webhook_url = os.environ.get('WEBHOOK_URL')
    if webhook_url:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        try:
            with urllib.request.urlopen(req) as response:
                print(f"Alert posted successfully: {response.status}")
        except Exception as e:
            print(f"Error posting alert to webhook: {e}")
    else:
        print("WEBHOOK_URL not set. Payload:")
        print(json.dumps(payload, indent=2))
        
    return {
        'statusCode': 200,
        'body': json.dumps(payload)
    }
