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
        
        # Process node data
        processed_nodes = []
        for node in nodes:
            name = node.get('name', 'N/A')
            status = node.get('status', 'unknown')
            gpu_total = node.get('gpu_total', 0)
            gpu_used = node.get('gpu_used', 0)
            gpu_free = node.get('gpu_free', 0)
            gpu_types = ', '.join(node.get('gpu_types', []))
            pool = node.get('labels', {}).get('g8s.host/pool', 'default')
            
            processed_nodes.append({
                'name': name,
                'status': status,
                'gpu_total': gpu_total,
                'gpu_used': gpu_used,
                'gpu_free': gpu_free,
                'gpu_types': gpu_types,
                'pool': pool
            })
        
        # Output in JSON format if requested
        if args.json:
            import json
            print(json.dumps(processed_nodes, indent=2))
        else:
            # Calculate column widths dynamically
            headers = ['NODE NAME', 'STATUS', 'GPU TOTAL', 'GPU USED', 'GPU FREE', 'GPU TYPE', 'POOL']
            col_widths = {'name': 15, 'status': 10, 'total': 10, 'used': 10, 'free': 10, 'type': 15, 'pool': 15}
            
            # First pass: calculate max widths
            for node in processed_nodes:
                col_widths['name'] = max(col_widths['name'], len(node['name']))
                col_widths['status'] = max(col_widths['status'], len(node['status']))
                col_widths['total'] = max(col_widths['total'], len(str(node['gpu_total'])))
                col_widths['used'] = max(col_widths['used'], len(str(node['gpu_used'])))
                col_widths['free'] = max(col_widths['free'], len(str(node['gpu_free'])))
                col_widths['type'] = max(col_widths['type'], len(node['gpu_types']))
                col_widths['pool'] = max(col_widths['pool'], len(node['pool']))
            
            # Print header
            header_line = f"{headers[0]:<{col_widths['name']}}  {headers[1]:<{col_widths['status']}}  {headers[2]:<{col_widths['total']}}  {headers[3]:<{col_widths['used']}}  {headers[4]:<{col_widths['free']}}  {headers[5]:<{col_widths['type']}}  {headers[6]:<{col_widths['pool']}}"
            print(header_line)
            
            # Print rows
            for node in processed_nodes:
                print(f"{node['name']:<{col_widths['name']}}  {node['status']:<{col_widths['status']}}  {node['gpu_total']:<{col_widths['total']}}  {node['gpu_used']:<{col_widths['used']}}  {node['gpu_free']:<{col_widths['free']}}  {node['gpu_types']:<{col_widths['type']}}  {node['pool']:<{col_widths['pool']}}")
        
        return 0
    except Exception as e:
        print(f"❌ Error getting nodes: {e}")
        import traceback
        traceback.print_exc()
        return 1


def get_labels_command(args):
    """Get node labels command"""
    try:
        client = PoolClient()
        
        # Get node info
        node = client.get_node(args.node_name)
        
        # Check if node exists
        if node is None:
            error = f"Node {args.node_name} not found"
            if args.json:
                import json
                print(json.dumps({"error": error}, indent=2))
            else:
                print(f"❌ {error}")
            return 1
        
        # Get node labels
        labels = node.get('labels', {})
        
        # Output in JSON format if requested
        if args.json:
            import json
            print(json.dumps(labels, indent=2))
        else:
            # If key is specified, only print that key's label
            if args.key:
                if args.key in labels:
                    print(f"{args.node_name} {args.key}: {labels[args.key]}")
                else:
                    print(f"❌ Label {args.key} not found on node {args.node_name}")
            else:
                # Print only g8s.host prefix labels
                print(f"🏷️  Labels for node {args.node_name}:")
                for key, value in labels.items():
                    if key.startswith('g8s.host'):
                        print(f"   {key}: {value}")
        
        return 0
    except Exception as e:
        print(f"❌ Error getting labels: {e}")
        import traceback
        traceback.print_exc()
        return 1


def label_node_command(args):
    """Add label to node command"""
    try:
        client = PoolClient()
        results = []
        
        # Helper function to convert camelCase to kebab-case and add prefix
        def process_label_key(key):
            # Convert camelCase to kebab-case
            kebab_key = ''
            for i, char in enumerate(key):
                if char.isupper() and i > 0:
                    kebab_key += '-' + char.lower()
                else:
                    kebab_key += char.lower()
            # Add g8s.host/ prefix
            return f"g8s.host/{kebab_key}"
        
        for node_name in args.node_name:
            if args.delete:
                # Remove label
                if args.label:
                    raw_key = args.label.split('=')[0] if '=' in args.label else args.label
                    processed_key = process_label_key(raw_key)
                    client._remove_node_label(node_name, processed_key)
                    result = {
                        "node": node_name,
                        "operation": "delete",
                        "label": processed_key,
                        "success": True,
                        "message": f"Successfully removed label {processed_key} from node {node_name}"
                    }
                    results.append(result)
                    if not args.json:
                        print(f"✅ Successfully removed label {processed_key} from node {node_name}")
                else:
                    error = "Must specify label to delete"
                    if args.json:
                        import json
                        print(json.dumps({"error": error}, indent=2))
                    else:
                        print(f"❌ {error}")
                    return 1
            else:
                # Add or update label
                if args.label:
                    if '=' not in args.label:
                        error = "Must specify label in key=value format"
                        if args.json:
                            import json
                            print(json.dumps({"error": error}, indent=2))
                        else:
                            print(f"❌ {error}")
                        return 1
                    
                    raw_key, value = args.label.split('=', 1)
                    processed_key = process_label_key(raw_key)
                    client._label_node(node_name, processed_key, value)
                    result = {
                        "node": node_name,
                        "operation": "add",
                        "label": {processed_key: value},
                        "success": True,
                        "message": f"Successfully labeled node {node_name} with {processed_key}={value}"
                    }
                    results.append(result)
                    if not args.json:
                        print(f"✅ Successfully labeled node {node_name} with {processed_key}={value}")
                else:
                    error = "Must specify label in key=value format"
                    if args.json:
                        import json
                        print(json.dumps({"error": error}, indent=2))
                    else:
                        print(f"❌ {error}")
                    return 1
        
        if args.json:
            import json
            print(json.dumps(results, indent=2))
        
        return 0
    except Exception as e:
        if args.json:
            import json
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"❌ Error labeling node: {e}")
        return 1





def describe_node_command(args):
    """Describe node details command"""
    try:
        client = PoolClient()
        node = client.get_node(args.node_name)
        
        # Check if node exists
        if node is None:
            error = f"Node '{args.node_name}' not found"
            if args.json:
                import json
                print(json.dumps({"error": error}, indent=2))
            else:
                print(f"❌ {error}")
            return 1
        
        # Output in JSON format if requested
        if args.json:
            import json
            print(json.dumps(node, indent=2))
            return 0
        
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
        
        try:
            # Create Kubernetes client to get events
            from gpuctl.client.base_client import KubernetesClient
            from datetime import datetime, timezone
            
            k8s_client = KubernetesClient()
            
            # Get events for this node
            field_selector = f"involvedObject.name={args.node_name},involvedObject.kind=Node"
            events = k8s_client.core_v1.list_namespaced_event(
                namespace="default",
                field_selector=field_selector,
                limit=10
            )
            
            if events.items:
                print(f"\n📋 Events:")
                
                def format_event_age(timestamp):
                    if not timestamp:
                        return "-"
                    try:
                        event_time = timestamp
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
                
                for i, event in enumerate(events.items):
                    event_type = event.type or 'Normal'
                    reason = event.reason or '-'
                    
                    timestamp = event.last_timestamp or event.first_timestamp or event.event_time
                    age = format_event_age(timestamp)
                    
                    source = event.source.component if event.source and event.source.component else '-'  
                    message = event.message or '-'
                    
                    print(f"  [{age}] {event_type} {reason}")
                    print(f"    From: {source}")
                    print(f"    Message: {message}")
                    
                    if i < len(events.items) - 1:
                        print()
        except Exception:
            pass
        
        return 0
    except Exception as e:
        if args.json:
            import json
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"❌ Error describing node: {e}")
        return 1
