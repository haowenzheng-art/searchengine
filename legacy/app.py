"""
Workflow Thief Arena - Web UI
支持运行 Agent 并展示完整分析结果
"""
import os
import json
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from pathlib import Path
import agent_enhanced as agent
from workflow_data import get_preset, PRESETS


app = Flask(__name__)
app.config['OUTPUT_DIR'] = 'output'
os.makedirs(app.config['OUTPUT_DIR'], exist_ok=True)

# 存储任务状态
tasks = {}


def run_agent_task(task_id: str, keyword: str, use_real_llm: bool = True):
    """后台运行Agent任务"""
    try:
        tasks[task_id]['status'] = 'running'
        tasks[task_id]['stage'] = '初始化...'
        tasks[task_id]['progress'] = 5

        # 设置进度回调
        def progress_callback(stage: str, progress: int):
            tasks[task_id]['stage'] = stage
            tasks[task_id]['progress'] = progress

        agent.set_progress_callback(progress_callback)

        result = agent.run_full_agent(keyword, app.config['OUTPUT_DIR'], use_real_llm=use_real_llm)

        if result:
            tasks[task_id]['status'] = 'completed'
            tasks[task_id]['progress'] = 100
            tasks[task_id]['result'] = result
            tasks[task_id]['files'] = find_output_files(keyword)
        else:
            tasks[task_id]['status'] = 'error'
            tasks[task_id]['error'] = '分析失败'
    except Exception as e:
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['error'] = str(e)


def find_output_files(keyword: str) -> dict:
    """查找输出文件"""
    output_dir = Path(app.config['OUTPUT_DIR'])
    files = {'json': None, 'docx': None, 'mermaid': None}

    safe_keyword = keyword.replace(' ', '_').replace('/', '_')
    for f in output_dir.glob(f"{safe_keyword}*"):
        if f.suffix == '.json':
            files['json'] = f.name
        elif f.suffix == '.docx':
            files['docx'] = f.name
        elif f.suffix == '.txt' and 'mermaid' in f.name:
            files['mermaid'] = f.name

    return files


@app.route('/')
def index():
    """首页"""
    english_presets = {k: v for k, v in PRESETS.items() if k in ['recruitment', 'insurance', 'ecommerce', 'customerservice']}
    return render_template('index.html', presets=english_presets)


@app.route('/api/task', methods=['POST'])
def create_task():
    """创建分析任务"""
    data = request.get_json()
    keyword = data.get('keyword', '').strip()
    use_real_llm = data.get('use_real_llm', True)

    if not keyword:
        return jsonify({'error': '请输入关键词'}), 400

    task_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    tasks[task_id] = {
        'status': 'pending',
        'keyword': keyword,
        'progress': 0,
        'stage': '',
        'result': None
    }

    # 后台运行
    thread = threading.Thread(target=run_agent_task, args=(task_id, keyword, use_real_llm))
    thread.start()

    return jsonify({'task_id': task_id})


@app.route('/api/task/<task_id>')
def get_task(task_id):
    """获取任务状态"""
    if task_id not in tasks:
        return jsonify({'error': '任务不存在'}), 404
    return jsonify(tasks[task_id])


@app.route('/api/preset/<key>')
def get_preset_data(key):
    """获取预设数据"""
    data = get_preset(key)
    if data:
        return jsonify({'result': data})
    return jsonify({'error': '预设不存在'}), 404


@app.route('/output/<filename>')
def download_file(filename):
    """下载输出文件"""
    return send_from_directory(app.config['OUTPUT_DIR'], filename, as_attachment=True)


if __name__ == '__main__':
    print("="*60)
    print("  Workflow Thief Arena - Web UI")
    print("="*60)
    print("访问: http://localhost:5000")
    print("="*60)
    app.run(debug=True, host='0.0.0.0', port=5000)
