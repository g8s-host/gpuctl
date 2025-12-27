import sys
from gpuctl.parser.base_parser import BaseParser, ParserError
from gpuctl.kind.training_kind import TrainingKind
from gpuctl.kind.inference_kind import InferenceKind
from gpuctl.kind.notebook_kind import NotebookKind
from gpuctl.client.job_client import JobClient
from gpuctl.client.log_client import LogClient


# Helper function: handle g8s-host prefix

def remove_prefix(name):
    """Remove g8s-host prefix from name, show only the original name from YAML file"""
    # For training jobs: g8s-host-training-xxx -> xxx
    if name.startswith("g8s-host-training-"):
        return name.split("g8s-host-training-")[1]
    # For inference jobs: g8s-host-inference-xxx -> xxx
    elif name.startswith("g8s-host-inference-"):
        return name.split("g8s-host-inference-")[1]
    # For notebook jobs: g8s-host-notebook-xxx -> xxx
    elif name.startswith("g8s-host-notebook-"):
        return name.split("g8s-host-notebook-")[1]
    # For compute jobs: g8s-host-compute-xxx -> xxx
    elif name.startswith("g8s-host-compute-"):
        return name.split("g8s-host-compute-")[1]
    # For other g8s-host- prefixed names: g8s-host-xxx -> xxx
    elif name.startswith("g8s-host-"):
        return name.split("g8s-host-")[1]
    return name

def add_prefix(name, job_type):
    """Add g8s-host prefix to name"""
    return f"g8s-host-{job_type}-{name}"


def create_job_command(args):
    """Create job command"""
    try:
        # Handle multiple files
        for file_path in args.file:
            print(f"\n📝 Processing file: {file_path}")
            
            # Parse YAML file
            parsed_obj = BaseParser.parse_yaml_file(file_path)

            # Create appropriate handler based on type
            if parsed_obj.kind == "training":
                handler = TrainingKind()
                result = handler.create_training_job(parsed_obj, args.namespace)
                # Display job_id with prefix removed
                display_job_id = remove_prefix(result['job_id'])
                print(f"✅ Successfully created {parsed_obj.kind} job: {display_job_id}")
                print(f"📊 Name: {result['name']}")
                print(f"📦 Namespace: {result['namespace']}")
                if 'resources' in result:
                    print(f"🖥️  Resources: {result['resources']}")
            elif parsed_obj.kind == "inference":
                handler = InferenceKind()
                result = handler.create_inference_service(parsed_obj, args.namespace)
                # Display job_id with prefix removed
                display_job_id = remove_prefix(result['job_id'])
                print(f"✅ Successfully created {parsed_obj.kind} service: {display_job_id}")
                print(f"📊 Name: {result['name']}")
                print(f"📦 Namespace: {result['namespace']}")
                if 'resources' in result:
                    print(f"🖥️  Resources: {result['resources']}")
                
                # Display Access Methods
                print("\n🌐 Access Methods:")
                
                try:
                    import subprocess
                    import json
                    
                    # Get Service info
                    service_base_name = result['name']
                    service_cmd = f"kubectl get svc g8s-host-svc-{service_base_name} -n g8s-host -o json"
                    service_output = subprocess.check_output(service_cmd, shell=True, text=True)
                    service_data = json.loads(service_output)
                    
                    # Get Node IP
                    node_cmd = f"kubectl get nodes -o json"
                    node_output = subprocess.check_output(node_cmd, shell=True, text=True)
                    node_data = json.loads(node_output)
                    node_ip = node_data['items'][0]['status']['addresses'][0]['address'] if node_data['items'] else 'N/A'
                    
                    # Get Service port info
                    node_port = service_data['spec']['ports'][0]['nodePort'] if service_data['spec']['ports'] and 'nodePort' in service_data['spec']['ports'][0] else 'N/A'
                    service_port = service_data['spec']['ports'][0]['port'] if service_data['spec']['ports'] else 'N/A'
                    target_port = service_data['spec']['ports'][0]['targetPort'] if service_data['spec']['ports'] else 'N/A'
                    
                    # Method 1: Access via Pod IP
                    print(f"   1. Pod IP Access:")
                    print(f"      - Pod is initializing, IP will be available once running")
                    print(f"      - Expected Port: {target_port if target_port != 'N/A' else service_port}")
                    
                    # Method 2: Access via NodePort
                    print(f"   2. NodePort Access:")
                    print(f"      - Node IP: {node_ip}")
                    print(f"      - NodePort: {node_port}")
                    if node_port != 'N/A':
                        print(f"      - Access: curl http://{node_ip}:{node_port}")
                    else:
                        print(f"      - NodePort not available")
                except Exception as e:
                    print(f"      - Access methods information not available yet")
            elif parsed_obj.kind == "notebook":
                handler = NotebookKind()
                result = handler.create_notebook(parsed_obj, args.namespace)
                # Display job_id with prefix removed
                display_job_id = remove_prefix(result['job_id'])
                print(f"✅ Successfully created {parsed_obj.kind} job: {display_job_id}")
                print(f"📊 Name: {result['name']}")
                print(f"📦 Namespace: {result['namespace']}")
                if 'resources' in result:
                    print(f"🖥️  Resources: {result['resources']}")
                
                # Display Access Methods
                print("\n🌐 Access Methods:")
                
                try:
                    import subprocess
                    import json
                    
                    # Get Service info
                    service_base_name = result['name']
                    service_cmd = f"kubectl get svc g8s-host-svc-{service_base_name} -n g8s-host -o json"
                    service_output = subprocess.check_output(service_cmd, shell=True, text=True)
                    service_data = json.loads(service_output)
                    
                    # Get Node IP
                    node_cmd = f"kubectl get nodes -o json"
                    node_output = subprocess.check_output(node_cmd, shell=True, text=True)
                    node_data = json.loads(node_output)
                    node_ip = node_data['items'][0]['status']['addresses'][0]['address'] if node_data['items'] else 'N/A'
                    
                    # Get Service port info
                    node_port = service_data['spec']['ports'][0]['nodePort'] if service_data['spec']['ports'] and 'nodePort' in service_data['spec']['ports'][0] else 'N/A'
                    service_port = service_data['spec']['ports'][0]['port'] if service_data['spec']['ports'] else 'N/A'
                    target_port = service_data['spec']['ports'][0]['targetPort'] if service_data['spec']['ports'] else 'N/A'
                    
                    # Method 1: Access via Pod IP
                    print(f"   1. Pod IP Access:")
                    print(f"      - Pod is initializing, IP will be available once running")
                    print(f"      - Expected Port: {target_port if target_port != 'N/A' else service_port}")
                    
                    # Method 2: Access via NodePort
                    print(f"   2. NodePort Access:")
                    print(f"      - Node IP: {node_ip}")
                    print(f"      - NodePort: {node_port}")
                    if node_port != 'N/A':
                        print(f"      - Access: curl http://{node_ip}:{node_port}")
                    else:
                        print(f"      - NodePort not available")
                except Exception as e:
                    print(f"      - Access methods information not available yet")
            elif parsed_obj.kind == "compute":
                from gpuctl.kind.compute_kind import ComputeKind
                handler = ComputeKind()
                result = handler.create_compute_service(parsed_obj, args.namespace)
                # Display job_id with prefix removed
                display_job_id = remove_prefix(result['job_id'])
                print(f"✅ Successfully created {parsed_obj.kind} service: {display_job_id}")
                print(f"📊 Name: {result['name']}")
                print(f"📦 Namespace: {result['namespace']}")
                if 'resources' in result:
                    print(f"🖥️  Resources: {result['resources']}")
                
                # Display Access Methods
                print("\n🌐 Access Methods:")
                
                try:
                    import subprocess
                    import json
                    
                    # Get Service info
                    service_base_name = result['name']
                    service_cmd = f"kubectl get svc g8s-host-svc-{service_base_name} -n g8s-host -o json"
                    service_output = subprocess.check_output(service_cmd, shell=True, text=True)
                    service_data = json.loads(service_output)
                    
                    # Get Node IP
                    node_cmd = f"kubectl get nodes -o json"
                    node_output = subprocess.check_output(node_cmd, shell=True, text=True)
                    node_data = json.loads(node_output)
                    node_ip = node_data['items'][0]['status']['addresses'][0]['address'] if node_data['items'] else 'N/A'
                    
                    # Get Service port info
                    node_port = service_data['spec']['ports'][0]['nodePort'] if service_data['spec']['ports'] and 'nodePort' in service_data['spec']['ports'][0] else 'N/A'
                    service_port = service_data['spec']['ports'][0]['port'] if service_data['spec']['ports'] else 'N/A'
                    target_port = service_data['spec']['ports'][0]['targetPort'] if service_data['spec']['ports'] else 'N/A'
                    
                    # Method 1: Access via Pod IP
                    print(f"   1. Pod IP Access:")
                    print(f"      - Pod is initializing, IP will be available once running")
                    print(f"      - Expected Port: {target_port if target_port != 'N/A' else service_port}")
                    
                    # Method 2: Access via NodePort
                    print(f"   2. NodePort Access:")
                    print(f"      - Node IP: {node_ip}")
                    print(f"      - NodePort: {node_port}")
                    if node_port != 'N/A':
                        print(f"      - Access: curl http://{node_ip}:{node_port}")
                    else:
                        print(f"      - NodePort not available")
                except Exception as e:
                    print(f"      - Access methods information not available yet")
            elif parsed_obj.kind == "pool" or parsed_obj.kind == "resource":
                # Resource pool creation logic
                from gpuctl.client.pool_client import PoolClient
                client = PoolClient()
                
                # Build resource pool configuration
                pool_config = {
                    "name": parsed_obj.metadata.name,
                    "description": parsed_obj.metadata.description,
                    "nodes": list(parsed_obj.nodes.keys())
                }
                
                # Create resource pool
                result = client.create_pool(pool_config)
                print(f"✅ Successfully created resource pool: {result['name']}")
                print(f"📊 Description: {parsed_obj.metadata.description}")
                print(f"📦 Node count: {len(parsed_obj.nodes)}")
                print(f"📋 Status: {result['status']}")
            else:
                print(f"❌ Unsupported kind: {parsed_obj.kind}")
                return 1

        return 0
    except ParserError as e:
        print(f"❌ Parser error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


def get_jobs_command(args):
    """Get jobs list command"""
    try:
        client = JobClient()
        
        # Build label filter criteria
        labels = {}
        if args.pool:
            labels["g8s.host/pool"] = args.pool
        if args.type:
            labels["g8s.host/job-type"] = args.type
        
        # Call API to get jobs list with filter criteria
        jobs = client.list_jobs(args.namespace, labels=labels, include_pods=True)
        
        # Helper function to calculate AGE
        def calculate_age(created_at_str):
            from datetime import datetime, timezone
            import math
            
            if not created_at_str:
                return "N/A"
            
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            delta = now - created_at
            
            seconds = delta.total_seconds()
            
            if seconds < 60:
                return f"{int(seconds)}s"
            elif seconds < 3600:
                return f"{int(seconds/60)}m"
            elif seconds < 86400:
                return f"{int(seconds/3600)}h"
            else:
                return f"{int(seconds/86400)}d"
        
        # Print jobs list
        print(f"{'JOB ID':<55} {'NAME':<20} {'KIND':<15} {'STATUS':<10} {'AGE':<10}")
        
        for job in jobs:
            # Calculate AGE
            age = calculate_age(job.get('creation_timestamp'))
            
            # Get job type
            job_type = job['labels'].get('g8s.host/job-type', 'unknown')
            
            # Use status info from job, which was set based on Pod actual status in _pod_to_dict
            status_dict = job.get("status", {})
            
            # Determine status based on active, succeeded, failed fields, consistent with k8s
            if status_dict.get('succeeded', 0) > 0:
                status = "Succeeded"
            elif status_dict.get('failed', 0) > 0:
                status = "Failed"
            elif status_dict.get('active', 0) > 0:
                status = "Running"
            else:
                status = "Pending"
            
            # Display name with prefix removed, show only original name from YAML file
            yaml_name = remove_prefix(job['name'])
            
            # Get job type
            job_type = job['labels'].get('g8s.host/job-type', 'unknown')
            
            # Extract base name from yaml_name
            parts = yaml_name.split('-')
            base_name = yaml_name
            
            if job_type == 'notebook':
                # StatefulSet Pod format: base-name-index (e.g., new-test-notebook-job-0)
                if len(parts) >= 2 and parts[-1].isdigit():
                    # Remove last numeric part
                    base_name = '-'.join(parts[:-1])
            elif len(parts) >= 3:
                # Deployment Pod format: base-name-deployment-hash-pod-suffix
                # Remove last two parts (deployment hash and pod suffix)
                base_name = '-'.join(parts[:-2])
            
            # For Pod instances, JOB ID shows Pod name without prefix, NAME shows original name from YAML
            display_job_id = remove_prefix(job['name'])
            print(f"{display_job_id:<55} {base_name:<20} {job_type:<15} {status:<10} {age:<10}")
        
        return 0
    except Exception as e:
        print(f"❌ Error getting jobs: {e}")
        return 1


def delete_job_command(args):
    """Delete job command"""
    try:
        client = JobClient()
        resource_type = None
        resource_name = None
        original_resource_name = None
        force = getattr(args, 'force', False)
        
        # Handle deletion by job_name
        job_name = getattr(args, 'job_name', None)
        if job_name:
            # delete job <job_name> command
            resource_name = job_name
            original_resource_name = resource_name
        elif args.file:
            # delete -f <yaml_file> command
            resource_type = None
            resource_name = None
            original_resource_name = None
            
            try:
                # Try full parsing (compatible with old logic)
                parsed_obj = BaseParser.parse_yaml_file(args.file)
                resource_type = parsed_obj.kind
                
                if resource_type in ["pool", "resource"]:
                    # Resource pool handling
                    if hasattr(parsed_obj, 'metadata') and hasattr(parsed_obj.metadata, 'name'):
                        resource_name = parsed_obj.metadata.name
                    elif hasattr(parsed_obj, 'pool') and hasattr(parsed_obj.pool, 'name'):
                        resource_name = parsed_obj.pool.name
                    else:
                        resource_name = args.file.replace('.yaml', '').replace('.yml', '')
                elif resource_type in ["training", "inference", "notebook", "compute"]:
                    # Job handling
                    if hasattr(parsed_obj, 'job') and hasattr(parsed_obj.job, 'name'):
                        resource_name = parsed_obj.job.name
                    else:
                        resource_name = args.file.replace('.yaml', '').replace('.yml', '')
                    original_resource_name = resource_name
            except Exception as e:
                # Full parsing failed, try simple YAML parsing to get necessary info
                import yaml
                with open(args.file, 'r') as f:
                    yaml_dict = yaml.safe_load(f)
                resource_type = yaml_dict['kind']
                
                if resource_type in ["pool", "resource"]:
                    # Resource pool handling
                    if 'metadata' in yaml_dict and 'name' in yaml_dict['metadata']:
                        resource_name = yaml_dict['metadata']['name']
                    elif 'pool' in yaml_dict and 'name' in yaml_dict['pool']:
                        resource_name = yaml_dict['pool']['name']
                    else:
                        resource_name = args.file.replace('.yaml', '').replace('.yml', '')
                elif resource_type in ["training", "inference", "notebook", "compute"]:
                    # Job handling
                    resource_name = yaml_dict['job']['name']
                    original_resource_name = resource_name
            
            # Handle resource pool deletion
            if resource_type in ["pool", "resource"]:
                # Delete resource pool
                from gpuctl.client.pool_client import PoolClient
                client = PoolClient()
                success = client.delete_pool(resource_name)
                if success:
                    print(f"✅ Successfully deleted resource pool: {resource_name}")
                    return 0
                else:
                    print(f"❌ Resource pool not found: {resource_name}")
                    return 1
        else:
            print("❌ Must provide YAML file path (-f/--file) or job name")
            return 1
        
        # Handle job deletion
        success = False
        
        # Get all jobs list to query actual job type
        all_jobs = client.list_jobs(args.namespace, include_pods=False)
        found_job = None
        
        # Find matching job in all jobs
        for job in all_jobs:
            job_name = job['name']
            # Check if matches original name (without prefix)
            if remove_prefix(job_name) == resource_name:
                found_job = job
                break
        
        if found_job:
            # Get actual job type and name from found job
            actual_job_type = found_job['labels'].get('g8s.host/job-type', 'unknown')
            actual_job_name = found_job['name']
            
            # Call appropriate delete method based on actual job type (delete entire Deployment/StatefulSet/Job)
            if actual_job_type == "training":
                # Training job: delete Job
                success = client.delete_job(actual_job_name, args.namespace, force)
            elif actual_job_type == "inference" or actual_job_type == "compute":
                # Inference or Compute job: delete Deployment and Service
                # Generate complete Service name
                service_name = f"g8s-host-svc-{resource_name}"
                # Delete Deployment
                deployment_deleted = client.delete_deployment(actual_job_name, args.namespace, force)
                # Delete Service
                service_deleted = client.delete_service(service_name, args.namespace)
                success = deployment_deleted and service_deleted
            elif actual_job_type == "notebook":
                # Notebook job: delete StatefulSet and Service
                # Generate complete Service name
                service_name = f"g8s-host-svc-{resource_name}"
                # Delete StatefulSet
                statefulset_deleted = client.delete_statefulset(actual_job_name, args.namespace, force)
                # Delete Service
                service_deleted = client.delete_service(service_name, args.namespace)
                success = statefulset_deleted and service_deleted
        else:
            # Try all possible prefixes
            job_types = ["training", "inference", "compute", "notebook"]
            for job_type in job_types:
                full_name = add_prefix(resource_name, job_type)
                if job_type == "training":
                    success = client.delete_job(full_name, args.namespace, force)
                elif job_type == "inference" or job_type == "compute":
                    deployment_deleted = client.delete_deployment(full_name, args.namespace, force)
                    service_deleted = client.delete_service(f"g8s-host-svc-{resource_name}", args.namespace)
                    success = deployment_deleted and service_deleted
                elif job_type == "notebook":
                    statefulset_deleted = client.delete_statefulset(full_name, args.namespace, force)
                    service_deleted = client.delete_service(f"g8s-host-svc-{resource_name}", args.namespace)
                    success = statefulset_deleted and service_deleted
                
                if success:
                    break
        
        if success:
            if force:
                print(f"✅ Successfully force deleted job: {original_resource_name}")
            else:
                print(f"✅ Successfully deleted job: {original_resource_name}")
            return 0
        else:
            print(f"❌ Job not found: {original_resource_name}")
            return 1

    except Exception as e:
        print(f"❌ Error deleting resource: {e}")
        return 1


def logs_job_command(args):
    """Get job logs command"""
    try:
        log_client = LogClient()
        job_client = JobClient()
        
        # Handle Pod name, ensure full name with prefix is used
        pod_name = args.job_name
        
        # If Pod name doesn't have prefix, try to find the full Pod name
        if not pod_name.startswith("g8s-host-"):
            # Get all Pods to find matching full name
            import subprocess
            import json
            
            try:
                # Get full info of all Pods
                cmd = f"kubectl get pods -n {args.namespace} -o json"
                output = subprocess.check_output(cmd, shell=True, text=True)
                pods_data = json.loads(output)
                
                # Find matching Pod
                for pod in pods_data['items']:
                    full_pod_name = pod['metadata']['name']
                    # Check if contains user-provided name
                    if pod_name in full_pod_name:
                        pod_name = full_pod_name
                        break
            except Exception as e:
                # If lookup fails, continue with original name
                pass
        
        if args.follow:
            # Use streaming logs, continuously fetch
            logs = log_client.stream_job_logs(pod_name, namespace=args.namespace, pod_name=pod_name)
            has_logs = False
            for log in logs:
                print(log)
                has_logs = True
            if not has_logs:
                print(f"ℹ️  No logs available for {args.job_name}. The Pod might be starting up or has no log output.")
        else:
            # Get logs once
            logs = log_client.get_job_logs(pod_name, namespace=args.namespace, tail=100, pod_name=pod_name)
            if not logs:
                print(f"ℹ️  No logs available for {args.job_name}. The Pod might be starting up or has no log output.")
            else:
                for log in logs:
                    print(log)
        
        return 0
    except Exception as e:
        print(f"❌ Error getting logs: {e}")
        return 1


def pause_job_command(args):
    """Pause job command"""
    try:
        client = JobClient()
        success = client.pause_job(args.job_name, args.namespace)
        if success:
            # Remove prefix when displaying
            display_name = remove_prefix(args.job_name)
            print(f"✅ Successfully paused job: {display_name}")
            return 0
        else:
            display_name = remove_prefix(args.job_name)
            print(f"❌ Failed to pause job: {display_name}")
            return 1
    except Exception as e:
        print(f"❌ Error pausing job: {e}")
        return 1


def resume_job_command(args):
    """Resume job command"""
    try:
        client = JobClient()
        success = client.resume_job(args.job_name, args.namespace)
        if success:
            # Remove prefix when displaying
            display_name = remove_prefix(args.job_name)
            print(f"✅ Successfully resumed job: {display_name}")
            return 0
        else:
            display_name = remove_prefix(args.job_name)
            print(f"❌ Failed to resume job: {display_name}")
            return 1
    except Exception as e:
        print(f"❌ Error resuming job: {e}")
        return 1


def describe_job_command(args):
    """Describe job details command"""
    try:
        client = JobClient()
        job = None
        
        # Check if resource name is already full name (with prefix)
        is_full_name = False
        if args.job_id.startswith("g8s-host-"):
            is_full_name = True
        
        # Try to get job directly
        job = client.get_job(args.job_id, args.namespace)
        
        if not job:
            # Get all jobs including Pod instances to query actual job
            all_jobs = client.list_jobs(args.namespace, include_pods=True)
            found_job = None
            
            # Find matching job in all jobs
            for job_item in all_jobs:
                job_name = job_item['name']
                # Check if matches full name or original name (without prefix)
                if job_name == args.job_id or remove_prefix(job_name) == args.job_id:
                    found_job = job_item
                    break
            
            if found_job:
                job = found_job
            else:
                # Try adding different prefixes again
                job_types = ["training", "inference", "notebook", "compute"]
                found = False
                for job_type in job_types:
                    prefixed_job_id = add_prefix(args.job_id, job_type)
                    job = client.get_job(prefixed_job_id, args.namespace)
                    if job:
                        found = True
                        break
                
                if not found:
                    print(f"❌ Job not found: {args.job_id}")
                    return 1
            
        # Print job details with prefix removed
        display_name = remove_prefix(job.get('name', 'N/A'))
        print(f"📋 Job Details: {display_name}")
        print(f"📊 Name: {display_name}")
        
        # Get job type and status
        job_type = job.get('labels', {}).get('g8s.host/job-type', 'unknown')
        status_dict = job.get('status', {})
        
        # Convert to status string consistent with k8s
        status = "Pending"
        if status_dict.get('succeeded', 0) > 0:
            status = "Succeeded"
        elif status_dict.get('failed', 0) > 0:
            # For inference jobs, failed status might be caused by pending status
            if job_type == "inference":
                status = "Pending"
            else:
                status = "Failed"
        elif status_dict.get('active', 0) > 0:
            status = "Running"
        
        # Calculate AGE
        from datetime import datetime, timezone
        def calculate_age(created_at_str):
            if not created_at_str:
                return "N/A"
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            delta = now - created_at
            seconds = delta.total_seconds()
            if seconds < 60:
                return f"{int(seconds)}s"
            elif seconds < 3600:
                return f"{int(seconds/60)}m"
            elif seconds < 86400:
                return f"{int(seconds/3600)}h"
            else:
                return f"{int(seconds/86400)}d"
        
        age = calculate_age(job.get('creation_timestamp'))
        
        print(f"🗂️  Kind: {job_type}")
        print(f"📈 Status: {status}")
        print(f"⏰ Age: {age}")
        print(f"🔧 Started: {job.get('start_time', 'N/A')}")
        print(f"🏁 Completed: {job.get('completion_time', 'N/A')}")
        print(f"📋 Priority: {job.get('labels', {}).get('g8s.host/priority', 'medium')}")
        print(f"🖥️  Pool: {job.get('labels', {}).get('g8s.host/pool', 'default')}")
        
        if 'resources' in job:
            print("\n💻 Resources:")
            resources = job['resources']
            print(f"   GPU: {resources.get('gpu', 'N/A')}")
            print(f"   CPU: {resources.get('cpu', 'N/A')}")
            print(f"   Memory: {resources.get('memory', 'N/A')}")
            print(f"   GPU Type: {resources.get('gpu_type', 'N/A')}")
        
        if 'metrics' in job:
            print("\n📊 Metrics:")
            metrics = job['metrics']
            print(f"   GPU Utilization: {metrics.get('gpuUtilization', 'N/A')}%")
            print(f"   Memory Usage: {metrics.get('memoryUsage', 'N/A')}")
            print(f"   Throughput: {metrics.get('throughput', 'N/A')}")
        
        # Get and display access methods
        job_type = job.get('labels', {}).get('g8s.host/job-type', '')
        if job_type in ['inference', 'compute', 'notebook']:
            print("\n🌐 Access Methods:")
            
            # Get full job name
            full_job_name = job.get('name', '')
            base_job_name = remove_prefix(full_job_name)
            
            # Extract service base name
            service_base_name = base_job_name
            
            # Handle different job types for service name extraction
            if job_type == 'notebook':
                # StatefulSet Pod format: base-name-index (e.g., new-test-notebook-job-0)
                parts = service_base_name.split('-')
                if len(parts) >= 2 and parts[-1].isdigit():
                    # Remove last numeric part
                    service_base_name = '-'.join(parts[:-1])
            elif len(service_base_name.split('-')) >= 3:
                # Deployment Pod format: base-name-deployment-hash-pod-suffix
                service_base_name = '-'.join(service_base_name.split('-')[:-2])
            
            # Get Service info first to get ports
            service_data = None
            service_found = True
            try:
                import subprocess
                import json
                
                service_cmd = f"kubectl get svc g8s-host-svc-{service_base_name} -n g8s-host -o json"
                service_output = subprocess.check_output(service_cmd, shell=True, text=True)
                service_data = json.loads(service_output)
            except Exception as e:
                service_found = False
            
            # Method 1: Access via Pod IP
            print(f"   1. Pod IP Access:")
            try:
                import subprocess
                import json
                
                # Get specific Pod info directly instead of all matching Pods
                pod_cmd = f"kubectl get pod {full_job_name} -n g8s-host -o json"
                pod_output = subprocess.check_output(pod_cmd, shell=True, text=True)
                pod_data = json.loads(pod_output)
                
                # Check Pod status
                pod_status = pod_data['status']['phase']
                if pod_status == 'Running':
                    # Only get and display Pod IP in Running state
                    pod_ip = pod_data['status'].get('podIP', 'N/A')
                    if service_found and service_data:
                        # Get Service port info
                        target_port = service_data['spec']['ports'][0]['targetPort'] if service_data['spec']['ports'] else 'N/A'
                        service_port = service_data['spec']['ports'][0]['port'] if service_data['spec']['ports'] else 'N/A'
                        pod_port = target_port if target_port != 'N/A' else service_port
                        print(f"      - Pod IP: {pod_ip}")
                        print(f"      - Port: {pod_port}")
                        print(f"      - Access: curl http://{pod_ip}:{pod_port}")
                    else:
                        print(f"      - Pod IP: {pod_ip}")
                else:
                    # Pod not in Running state, don't show IP
                    print(f"      - Pod is {pod_status}, no IP available")
            except subprocess.CalledProcessError:
                print(f"      - Pod {full_job_name} not found")
            except Exception as e:
                print(f"      - Failed to get pod info: {e}")
            
            # Method 2: Access via NodePort
            print(f"   2. NodePort Access:")
            if not service_found:
                # Service not found, show friendly message
                print(f"      - Service not available for this job")
            else:
                try:
                    import subprocess
                    import json
                    
                    if service_data:
                        # Get Service port info
                        node_port = service_data['spec']['ports'][0]['nodePort'] if service_data['spec']['ports'] and 'nodePort' in service_data['spec']['ports'][0] else 'N/A'
                        
                        # Get Node IP
                        node_cmd = f"kubectl get nodes -o json"
                        node_output = subprocess.check_output(node_cmd, shell=True, text=True)
                        node_data = json.loads(node_output)
                        node_ip = node_data['items'][0]['status']['addresses'][0]['address'] if node_data['items'] else 'N/A'
                        
                        # Check Pod status, if Pod is not Running, NodePort access is not available
                        pod_cmd = f"kubectl get pod {full_job_name} -n g8s-host -o json"
                        pod_output = subprocess.check_output(pod_cmd, shell=True, text=True)
                        pod_data = json.loads(pod_output)
                        pod_status = pod_data['status']['phase']
                        
                        if pod_status == 'Running':
                            print(f"      - Node IP: {node_ip}")
                            print(f"      - NodePort: {node_port}")
                            if node_port != 'N/A':
                                print(f"      - Access: curl http://{node_ip}:{node_port}")
                            else:
                                print(f"      - NodePort not available")
                        else:
                            # Pod not in Running state, NodePort access not available
                            print(f"      - Pod is {pod_status}, NodePort access unavailable")
                    else:
                        print(f"      - No service found for this job")
                except Exception as e:
                    print(f"      - Failed to get service info: {e}")
        
        return 0
    except Exception as e:
        print(f"❌ Error describing job: {e}")
        return 1
