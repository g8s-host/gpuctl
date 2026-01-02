from gpuctl.client.pool_client import PoolClient


def get_nodes_command(args):
    """Get nodes list command"""
    try:
        client = PoolClient()
        
        # Build filter criteria
        filters = {}
        if args.pool:
            filters["pool"] = args.pool
        if args.gpu_type:
            filters["gpu_type"] = args.gpu_type
        
        # Call API to get nodes list with filter criteria
        nodes = client.list_nodes(filters=filters)
        
        # Print nodes list
        print(f"{'NODE NAME':<30} {'STATUS':<10} {'GPU TOTAL':<10} {'GPU USED':<10} {'GPU FREE':<10} {'GPU TYPE':<15} {'POOL':<20}")
        
        for node in nodes:
            # Safely access dictionary fields with default values for missing cases
            name = node.get('name', 'N/A')
            status = node.get('status', 'unknown')
            gpu_total = node.get('gpu_total', 0)
            gpu_used = node.get('gpu_used', 0)
            gpu_free = node.get('gpu_free', 0)
            gpu_types = ', '.join(node.get('gpu_types', []))
            pool = node.get('labels', {}).get('g8s.host/pool', 'default')
            
            print(f"{name:<30} {status:<10} {gpu_total:<10} {gpu_used:<10} {gpu_free:<10} {gpu_types:<15} {pool:<20}")
        
        return 0
    except Exception as e:
        print(f"❌ Error getting nodes: {e}")
        return 1


def get_labels_command(args):
    """Get node labels command"""
    try:
        client = PoolClient()
        
        # Get node info
        node = client.get_node(args.node_name)
        
        # Get node labels
        labels = node.get('labels', {})
        
        # If key is specified, only print that key's label
        if args.key:
            if args.key in labels:
                print(f"{args.node_name} {args.key}: {labels[args.key]}")
            else:
                print(f"❌ Label {args.key} not found on node {args.node_name}")
        else:
            # Print all labels
            print(f"🏷️  Labels for node {args.node_name}:")
            for key, value in labels.items():
                print(f"   {key}: {value}")
        
        return 0
    except Exception as e:
        print(f"❌ Error getting labels: {e}")
        return 1


def label_node_command(args):
    """Add label to node command"""
    try:
        client = PoolClient()
        
        for node_name in args.node_name:
            if args.delete:
                # Remove label
                if args.label:
                    key = args.label.split('=')[0]
                    client._remove_node_label(node_name, key)
                    print(f"✅ Successfully removed label {key} from node {node_name}")
                else:
                    print(f"❌ Must specify label to delete")
                    return 1
            else:
                # Add or update label
                if args.label:
                    key, value = args.label.split('=')
                    client._label_node(node_name, key, value)
                    print(f"✅ Successfully labeled node {node_name} with {key}={value}")
                else:
                    print(f"❌ Must specify label in key=value format")
                    return 1
        
        return 0
    except Exception as e:
        print(f"❌ Error labeling node: {e}")
        return 1


def add_node_to_pool_command(args):
    """Add node to pool command"""
    try:
        client = PoolClient()
        result = client.add_nodes_to_pool(args.pool, args.node_name)
        
        if result['success']:
            print(f"✅ Successfully added nodes {', '.join(result['success'])} to pool {args.pool}")
        
        if result['failed']:
            for failure in result['failed']:
                print(f"❌ Failed to add node {failure['node']}: {failure['error']}")
        
        return 0
    except Exception as e:
        print(f"❌ Error adding node to pool: {e}")
        return 1


def remove_node_from_pool_command(args):
    """Remove node from pool command"""
    try:
        client = PoolClient()
        result = client.remove_nodes_from_pool(args.pool, args.node_name)
        
        if result['success']:
            print(f"✅ Successfully removed nodes {', '.join(result['success'])} from pool {args.pool}")
        
        if result['failed']:
            for failure in result['failed']:
                print(f"❌ Failed to remove node {failure['node']}: {failure['error']}")
        
        return 0
    except Exception as e:
        print(f"❌ Error removing node from pool: {e}")
        return 1


def describe_node_command(args):
    """Describe node details command"""
    try:
        client = PoolClient()
        node = client.get_node(args.node_name)
        
        # Print node details
        print(f"📋 Node Details: {args.node_name}")
        print(f"📊 Name: {node.get('name', 'N/A')}")
        print(f"📈 Status: {node.get('status', 'unknown')}")
        print(f"🔧 K8s Status: {node.get('k8s_status', 'N/A')}")
        print(f"🖥️  Pool: {node.get('labels', {}).get('g8s.host/pool', 'default')}")
        
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
        
        age = calculate_age(node.get('created_at'))
        print(f"⏰ Age: {age}")
        print(f"⏰ Last Updated: {node.get('last_updated_at', 'N/A')}")
        
        if 'resources' in node:
            print("\n💻 Resources:")
            resources = node['resources']
            print(f"   CPU Total: {resources.get('cpu_total', 'N/A')}")
            print(f"   CPU Used: {resources.get('cpu_used', 'N/A')}")
            print(f"   Memory Total: {resources.get('memory_total', 'N/A')}")
            print(f"   Memory Used: {resources.get('memory_used', 'N/A')}")
            print(f"   GPU Total: {resources.get('gpu_total', 'N/A')}")
            print(f"   GPU Used: {resources.get('gpu_used', 'N/A')}")
            print(f"   GPU Free: {resources.get('gpu_free', 'N/A')}")
        
        if 'gpu_detail' in node:
            print("\n🖥️  GPU Details:")
            for gpu in node['gpu_detail']:
                print(f"   GPU {gpu.get('gpuId', 'N/A')}:")
                print(f"      Type: {gpu.get('type', 'N/A')}")
                print(f"      Status: {gpu.get('status', 'N/A')}")
                print(f"      Utilization: {gpu.get('utilization', 'N/A')}%")
                print(f"      Memory Usage: {gpu.get('memoryUsage', 'N/A')}")
        
        if 'labels' in node:
            print("\n🏷️  Labels:")
            for key, value in node['labels'].items():
                print(f"   {key}: {value}")
        
        if 'running_jobs' in node:
            print("\n📋 Running Jobs:")
            for job in node['running_jobs']:
                print(f"   - {job.get('name', 'N/A')} (GPU: {job.get('gpu', 0)})")
        
        import subprocess
        import json
        try:
            events_cmd = f"kubectl get events -n default --field-selector involvedObject.name={args.node_name},involvedObject.kind=Node -o json"
            events_output = subprocess.check_output(events_cmd, shell=True, text=True)
            events_data = json.loads(events_output)
            
            if events_data.get('items'):
                print(f"\n📋 Events:")
                
                for i, event in enumerate(events_data['items'][:10]):
                    event_type = event.get('type', 'Normal')
                    reason = event.get('reason', '-')
                    
                    timestamp = event.get('lastTimestamp') or event.get('firstTimestamp') or event.get('eventTime')
                    if timestamp:
                        if isinstance(timestamp, str) and '.' in timestamp:
                            timestamp = timestamp.split('.')[0] + 'Z'
                    
                    from datetime import datetime, timezone
                    def format_event_age(ts):
                        if not ts:
                            return "-"
                        try:
                            event_time = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                            now = datetime.now(timezone.utc)
                            delta = now - event_time
                            seconds = delta.total_seconds()
                            if seconds < 0:
                                seconds = 0
                            if seconds < 60:
                                return f"{int(seconds)}s"
                            elif seconds < 3600:
                                return f"{int(seconds/60)}m"
                            elif seconds < 86400:
                                return f"{int(seconds/3600)}h"
                            else:
                                return f"{int(seconds/86400)}d"
                        except Exception:
                            return "-"
                    
                    age = format_event_age(timestamp)
                    source = event.get('source', {}).get('component', '-') or event.get('reportingComponent', '-')
                    message = event.get('message', '-')
                    
                    print(f"  [{age}] {event_type} {reason}")
                    print(f"    From: {source}")
                    print(f"    Message: {message}")
                    
                    if i < len(events_data['items']) - 1:
                        print()
        except Exception:
            pass
        
        return 0
    except Exception as e:
        print(f"❌ Error describing node: {e}")
        return 1
