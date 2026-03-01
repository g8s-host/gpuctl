import unittest
from gpuctl.cli.job_mapper import _map_notebook_job


class TestNotebookJobMapper(unittest.TestCase):
    """测试notebook作业映射函数"""

    def setUp(self):
        """设置测试数据"""
        # 基础映射数据
        self.base_mapped = {
            'kind': 'notebook',
            'job': {
                'name': 'test-notebook',
                'namespace': 'default',
                'priority': 'medium',
                'description': 'Test job'
            }
        }

        # 带有哈希后缀的作业名称
        self.base_mapped_with_hash = {
            'kind': 'notebook',
            'job': {
                'name': 'test-notebook-abc123',
                'namespace': 'default',
                'priority': 'medium',
                'description': 'Test job'
            }
        }

        # 基础Kubernetes资源数据
        self.base_job_data = {
            'spec': {
                'template': {
                    'spec': {
                        'containers': [
                            {
                                'command': ['jupyter-lab', '--ip=0.0.0.0', '--port=8888', '--no-browser', '--allow-root'],
                                'image': 'jupyter/minimal-notebook:latest',
                                'resources': {
                                    'limits': {
                                        'cpu': '1',
                                        'memory': '2Gi'
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }

    def test_map_notebook_job_basic(self):
        """测试基本的notebook作业映射"""
        # 调用映射函数
        result = _map_notebook_job(self.base_job_data, self.base_mapped)

        # 验证结果
        self.assertEqual(result['kind'], 'notebook')
        self.assertEqual(result['version'], 'v0.1')
        self.assertEqual(result['job']['name'], 'test-notebook')
        self.assertEqual(result['job']['namespace'], 'default')
        self.assertEqual(result['job']['priority'], 'medium')
        self.assertEqual(result['job']['description'], 'Test job')
        self.assertEqual(result['environment']['image'], 'jupyter/minimal-notebook:latest')
        self.assertEqual(result['environment']['command'], ['jupyter-lab', '--ip=0.0.0.0', '--port=8888', '--no-browser', '--allow-root'])
        self.assertEqual(result['service']['port'], 8888)  # 默认值
        self.assertEqual(result['resources']['pool'], 'default')  # 默认值
        self.assertEqual(result['resources']['cpu'], 1)
        self.assertEqual(result['resources']['memory'], '2Gi')
        self.assertEqual(result['resources']['gpu'], 0)  # 默认值
        self.assertEqual(result['resources']['gpuShare'], '2Gi')  # 默认值

    def test_map_notebook_job_with_hash_suffix(self):
        """测试带有哈希后缀的notebook作业映射"""
        # 调用映射函数
        result = _map_notebook_job(self.base_job_data, self.base_mapped_with_hash)

        # 验证结果，作业名称应该移除哈希后缀
        self.assertEqual(result['job']['name'], 'test-notebook')

    def test_map_notebook_job_with_args(self):
        """测试带有参数的notebook作业映射"""
        # 创建带有参数的作业数据
        job_with_args = {
            **self.base_job_data,
            'spec': {
                'template': {
                    'spec': {
                        'containers': [
                            {
                                **self.base_job_data['spec']['template']['spec']['containers'][0],
                                'args': ['--NotebookApp.token=', '--NotebookApp.password=']
                            }
                        ]
                    }
                }
            }
        }

        # 调用映射函数
        result = _map_notebook_job(job_with_args, self.base_mapped)

        # 验证结果，应该包含args字段
        self.assertIn('args', result['environment'])
        self.assertEqual(result['environment']['args'], ['--NotebookApp.token=', '--NotebookApp.password='])

    def test_map_notebook_job_with_env(self):
        """测试带有环境变量的notebook作业映射"""
        # 创建带有环境变量的作业数据
        job_with_env = {
            **self.base_job_data,
            'spec': {
                'template': {
                    'spec': {
                        'containers': [
                            {
                                **self.base_job_data['spec']['template']['spec']['containers'][0],
                                'env': [
                                    {'name': 'JUPYTER_ENABLE_LAB', 'value': 'yes'}
                                ]
                            }
                        ]
                    }
                }
            }
        }

        # 调用映射函数
        result = _map_notebook_job(job_with_env, self.base_mapped)

        # 验证结果，应该包含env字段
        self.assertIn('env', result['environment'])
        self.assertEqual(len(result['environment']['env']), 1)
        self.assertEqual(result['environment']['env'][0]['name'], 'JUPYTER_ENABLE_LAB')
        self.assertEqual(result['environment']['env'][0]['value'], 'yes')

    def test_map_notebook_job_with_workdirs(self):
        """测试带有工作目录的notebook作业映射"""
        # 创建带有工作目录的作业数据
        job_with_workdirs = {
            **self.base_job_data,
            'spec': {
                'template': {
                    'spec': {
                        'containers': [
                            self.base_job_data['spec']['template']['spec']['containers'][0]
                        ],
                        'volumes': [
                            {
                                'hostPath': {
                                    'path': '/home/jovyan/work'
                                },
                                'name': 'workdir-0'
                            }
                        ]
                    }
                }
            }
        }

        # 调用映射函数
        result = _map_notebook_job(job_with_workdirs, self.base_mapped)

        # 验证结果，应该包含storage.workdirs字段
        self.assertIn('storage', result)
        self.assertIn('workdirs', result['storage'])
        self.assertEqual(len(result['storage']['workdirs']), 1)
        self.assertEqual(result['storage']['workdirs'][0]['path'], '/home/jovyan/work')

    def test_map_notebook_job_with_ports(self):
        """测试带有端口的notebook作业映射"""
        # 创建带有端口的作业数据
        job_with_ports = {
            **self.base_job_data,
            'spec': {
                'template': {
                    'spec': {
                        'containers': [
                            {
                                **self.base_job_data['spec']['template']['spec']['containers'][0],
                                'ports': [
                                    {'containerPort': 9999}
                                ]
                            }
                        ]
                    }
                }
            }
        }

        # 调用映射函数
        result = _map_notebook_job(job_with_ports, self.base_mapped)

        # 验证结果，端口应该被正确提取
        self.assertEqual(result['service']['port'], 9999)

    def test_map_notebook_job_with_labels(self):
        """测试带有标签的notebook作业映射"""
        # 创建带有标签的作业数据
        job_with_labels = {
            **self.base_job_data,
            'labels': {
                'g8s.host/pool': 'custom-notebook-pool'
            }
        }

        # 调用映射函数
        result = _map_notebook_job(job_with_labels, self.base_mapped)

        # 验证结果，应该使用标签中的pool值
        self.assertEqual(result['resources']['pool'], 'custom-notebook-pool')


if __name__ == '__main__':
    unittest.main()
