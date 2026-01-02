from gpuctl.client.pool_client import PoolClient


def get_pools_command(args):
    """Get resource pools list command"""
    try:
        client = PoolClient()
        pools = client.list_pools()
        
        # Calculate column widths dynamically
        headers = ['POOL NAME', 'STATUS', 'GPU TOTAL', 'GPU USED', 'GPU FREE', 'GPU TYPE', 'NODE COUNT']
        col_widths = {'name': 15, 'status': 10, 'total': 10, 'used': 10, 'free': 10, 'type': 15, 'count': 10}
        
        pool_rows = []
        for pool in pools:
            pool_rows.append({
                'name': pool['name'],
                'status': pool['status'],
                'total': str(pool['gpu_total']),
                'used': str(pool['gpu_used']),
                'free': str(pool['gpu_free']),
                'type': ', '.join(pool['gpu_types']),
                'count': str(len(pool['nodes']))
            })
            
            col_widths['name'] = max(col_widths['name'], len(pool['name']))
            col_widths['status'] = max(col_widths['status'], len(pool['status']))
            col_widths['total'] = max(col_widths['total'], len(str(pool['gpu_total'])))
            col_widths['used'] = max(col_widths['used'], len(str(pool['gpu_used'])))
            col_widths['free'] = max(col_widths['free'], len(str(pool['gpu_free'])))
            col_widths['type'] = max(col_widths['type'], len(', '.join(pool['gpu_types'])))
            col_widths['count'] = max(col_widths['count'], len(str(len(pool['nodes']))))
        
        print(f"{headers[0]:<{col_widths['name']}}  {headers[1]:<{col_widths['status']}}  {headers[2]:<{col_widths['total']}}  {headers[3]:<{col_widths['used']}}  {headers[4]:<{col_widths['free']}}  {headers[5]:<{col_widths['type']}}  {headers[6]:<{col_widths['count']}}")
        
        for row in pool_rows:
            print(f"{row['name']:<{col_widths['name']}}  {row['status']:<{col_widths['status']}}  {row['total']:<{col_widths['total']}}  {row['used']:<{col_widths['used']}}  {row['free']:<{col_widths['free']}}  {row['type']:<{col_widths['type']}}  {row['count']:<{col_widths['count']}}")
        
        return 0
    except Exception as e:
        print(f"❌ Error getting pools: {e}")
        return 1


def create_pool_command(args):
    """Create resource pool command"""
    try:
        client = PoolClient()
        
        pool_config = {
            "name": args.name,
            "description": args.description,
            "nodes": args.nodes,
            "gpu_type": args.gpu_type,
            "quota": args.quota
        }
        
        result = client.create_pool(pool_config)
        print(f"✅ Successfully created pool: {result['name']}")
        print(f"📊 Status: {result['status']}")
        print(f"📦 Message: {result['message']}")
        
        return 0
    except Exception as e:
        print(f"❌ Error creating pool: {e}")
        return 1


def delete_pool_command(args):
    """Delete resource pool command"""
    try:
        client = PoolClient()
        success = client.delete_pool(args.pool_name)
        
        if success:
            print(f"✅ Successfully deleted pool: {args.pool_name}")
            return 0
        else:
            print(f"❌ Pool not found: {args.pool_name}")
            return 1
    except Exception as e:
        print(f"❌ Error deleting pool: {e}")
        return 1


def describe_pool_command(args):
    """Describe resource pool details command"""
    try:
        client = PoolClient()
        pool = client.get_pool(args.pool_name)
        
        # Print resource pool details
        print(f"📋 Pool Details: {args.pool_name}")
        print(f"📊 Name: {pool.get('name', 'N/A')}")
        print(f"📝 Description: {pool.get('description', 'N/A')}")
        print(f"📈 Status: {pool.get('status', 'unknown')}")
        print(f"🖥️  GPU Total: {pool.get('gpu_total', 'N/A')}")
        print(f"📊 GPU Used: {pool.get('gpu_used', 'N/A')}")
        print(f"🆓 GPU Free: {pool.get('gpu_free', 'N/A')}")
        print(f"🔧 GPU Types: {', '.join(pool.get('gpu_types', []))}")
        print(f"🖥️  Node Count: {len(pool.get('nodes', []))}")
        
        if 'quota' in pool:
            print("\n📊 Quota:")
            quota = pool['quota']
            print(f"   Max Jobs: {quota.get('maxJobs', 'N/A')}")
            print(f"   Max GPU Per Job: {quota.get('maxGpuPerJob', 'N/A')}")
        
        if 'nodes' in pool and pool['nodes']:
            print("\n🖥️  Nodes:")
            for node in pool['nodes']:
                print(f"   - {node}")
        
        if 'jobs' in pool and pool['jobs']:
            print("\n📋 Running Jobs:")
            for job in pool['jobs']:
                print(f"   - {job['name']} (GPU: {job.get('gpu', 0)})")
        
        return 0
    except Exception as e:
        print(f"❌ Error describing pool: {e}")
        return 1
