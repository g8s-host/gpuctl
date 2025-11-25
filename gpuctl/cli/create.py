import argparse
import sys
from gpuctl.parser.base_parser import BaseParser, ParserError

from gpuctl.kind.training_kind import TrainingKind
from gpuctl.kind.inference_kind import InferenceKind
from gpuctl.kind.notebook_kind import NotebookKind


def create_command(args):
    """处理create命令"""
    try:
        # 解析YAML文件
        parsed_obj = BaseParser.parse_yaml_file(args.file)

        # 根据类型创建相应处理器
        if parsed_obj.kind == "training":
            handler = TrainingKind()
            result = handler.create_training_job(parsed_obj, args.namespace)
        elif parsed_obj.kind == "inference":
            handler = InferenceKind()
            result = handler.create_inference_service(parsed_obj, args.namespace)
        elif parsed_obj.kind == "notebook":
            handler = NotebookKind()
            result = handler.create_notebook(parsed_obj, args.namespace)
        else:
            print(f"Unsupported kind: {parsed_obj.kind}")
            return 1

        print(f"✅ Successfully created {parsed_obj.kind} job: {result['job_id']}")
        print(f"📊 Name: {result['name']}")
        print(f"📦 Namespace: {result['namespace']}")
        if 'resources' in result:
            print(f"🖥️  Resources: {result['resources']}")

        return 0

    except ParserError as e:
        print(f"❌ Parser error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(description='Create GPU job from YAML')
    parser.add_argument('-f', '--file', required=True, help='YAML file path')
    parser.add_argument('-n', '--namespace', default='default', help='Kubernetes namespace')

    args = parser.parse_args()
    sys.exit(create_command(args))


if __name__ == '__main__':
    main()