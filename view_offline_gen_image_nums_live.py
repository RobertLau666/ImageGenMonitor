import pandas as pd
import numpy as np
import gradio as gr
import time
from datetime import datetime, timedelta
import re
import copy
import json
import os
import socket


def create_dir_or_file(path):
    if not os.path.exists(path):
        file_name, file_extension = os.path.splitext(path)
        if file_extension == "":
            os.makedirs(path, exist_ok=True)
        else:
            if not os.path.exists(path):
                with open(path, 'w') as file:
                    pass

def get_logs():
    create_dir_or_file(save_log_dir)
    local_private_host = socket.gethostbyname(socket.gethostname())
    for i, public_private_dict in host_dict.items():
        if public_private_dict['private'] != local_private_host:
            os.system(f"rsync -avz worker@{public_private_dict['private']}:{log_path} {save_log_dir}/{public_private_dict['public']}_{log_path.split('/')[-1]}")
        else:
            local_public_host = public_private_dict['public']
    os.system(f"cp -r {log_path} {save_log_dir}/{local_public_host}_{log_path.split('/')[-1]}")

    log_file_paths = []
    log_file_names = os.listdir(save_log_dir)
    for log_file_name in log_file_names:
        log_file_paths.append(os.path.join(save_log_dir, log_file_name))

    return log_file_paths

def record_json(log_file_paths):
    record_dict = {}
    for log_file in log_file_paths:
        ip = log_file.split('/')[-1].split('_')[0]
        with open(log_file, "r") as f:
            log_lines = f.readlines()

        target_date = "2024-"
        target_logs = [line.strip() for line in log_lines if line.startswith(target_date)]

        # 找出格式为后面都是空格的元素
        pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s*$"
        boundary_indices = [i for i, log in enumerate(target_logs) if re.match(pattern, log)]

        # 使用边界索引将target_logs分组
        groups_temp = []
        start = 0
        for boundary_index in boundary_indices:
            log_group = target_logs[start:boundary_index]
            groups_temp.append(log_group)
            start = boundary_index

        # 最后一个分界线之后的元素也需要添加到最后一个小组中
        groups_temp.append(target_logs[start:])

        # 输出每个小组
        groups = []
        sub_string = "main_execution_done_times"
        for i, group in enumerate(groups_temp):
            is_group = True if any(sub_string in element for element in group) else False
            if is_group:
                groups.append(group)

        for i, group in enumerate(groups):
            npc_name_num, npc_names, mode, round_num, done_time = None, None, None, None, None
            for log in group:
                temp_dict = {}
                npc_name_list_match = re.search(r"NPC_name_list\s+(\d+):\s+(\[.*\])", log)
                if npc_name_list_match:
                    npc_name_num = int(npc_name_list_match.group(1))
                    npc_names = npc_name_list_match.group(2)
                    
                    date = log.split(' ')[0]
                    if date not in record_dict:
                        record_dict[date] = {}
                    if ip not in record_dict[date]:
                        record_dict[date][ip] = {}

                mode_match = re.search(r"    mode\s+(.*)", log)
                if mode_match:
                    mode = mode_match.group(1)
                    
                round_num_match = re.search(r"round_num\s+(.*)", log)
                if round_num_match:
                    round_num = int(round_num_match.group(1))

                done_time_match = re.search(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+4\. start\s+done", log)
                if done_time_match:
                    done_time = done_time_match.group(1)
                    
            temp_dict['npc_name_num'] = npc_name_num
            temp_dict['npc_names'] = npc_names
            temp_dict['mode'] = mode
            temp_dict['round_num'] = round_num
            temp_dict['done_time'] = done_time
            
            record_dict[date][ip][i] = temp_dict

    record_dict_new = copy.deepcopy(record_dict)
    all_chat_NPC_nums = 0
    all_wishwell_NPC_nums = 0
    all_chat_image_nums = 0
    all_wishwell_image_nums = 0
    for date, date_dict in record_dict.items():
        chat_NPC_nums = 0
        wishwell_NPC_nums = 0
        for ip, ip_dict in date_dict.items():
            for id, id_dict in ip_dict.items():
                if id_dict["mode"] == "chat":
                    chat_NPC_nums += id_dict["npc_name_num"]
                elif id_dict["mode"] == "wishwell":
                    wishwell_NPC_nums += id_dict["npc_name_num"]
        record_dict_new[date]["all_ips"] = {}
        record_dict_new[date]["all_ips"]["chat_NPC_nums"] = chat_NPC_nums
        record_dict_new[date]["all_ips"]["wishwell_NPC_nums"] = wishwell_NPC_nums
        record_dict_new[date]["all_ips"]["NPC_nums"] = record_dict_new[date]["all_ips"]["chat_NPC_nums"] + record_dict_new[date]["all_ips"]["wishwell_NPC_nums"]
        record_dict_new[date]["all_ips"]["chat_image_nums"] = chat_NPC_nums * mode_info_dict["chat"]["group"] * mode_info_dict["chat"]["imgs"] *  mode_info_dict["chat"]["deform_percent"]
        record_dict_new[date]["all_ips"]["wishwell_image_nums"] = wishwell_NPC_nums * mode_info_dict["wishwell"]["group"] * mode_info_dict["wishwell"]["imgs"] *  mode_info_dict["wishwell"]["deform_percent"]
        record_dict_new[date]["all_ips"]["image_nums"] = record_dict_new[date]["all_ips"]["chat_image_nums"] + record_dict_new[date]["all_ips"]["wishwell_image_nums"]
        all_chat_NPC_nums += record_dict_new[date]["all_ips"]["chat_NPC_nums"]
        all_wishwell_NPC_nums += record_dict_new[date]["all_ips"]["wishwell_NPC_nums"]
        all_chat_image_nums += record_dict_new[date]["all_ips"]["chat_image_nums"]
        all_wishwell_image_nums += record_dict_new[date]["all_ips"]["wishwell_image_nums"]
    
    record_dict_new["all_dates"] = {}
    record_dict_new["all_dates"]["all_chat_NPC_nums"] = all_chat_NPC_nums
    record_dict_new["all_dates"]["all_wishwell_NPC_nums"] = all_wishwell_NPC_nums
    record_dict_new["all_dates"]["all_NPC_nums"] = record_dict_new["all_dates"]["all_chat_NPC_nums"] + record_dict_new["all_dates"]["all_wishwell_NPC_nums"]
    record_dict_new["all_dates"]["all_chat_image_nums"] = all_chat_image_nums
    record_dict_new["all_dates"]["all_wishwell_image_nums"] = all_wishwell_image_nums
    record_dict_new["all_dates"]["all_image_nums"] = record_dict_new["all_dates"]["all_chat_image_nums"] + record_dict_new["all_dates"]["all_wishwell_image_nums"]

    with open(f'view_offline_gen_image_nums_record.json', 'w', encoding='utf-8') as file:
        file.write(json.dumps(record_dict_new, indent=4, ensure_ascii=False))
    
    return record_dict_new

def generate_bar_chart(record_dict_new):
    date_list = []
    NPC_nums_list = []
    image_nums_list = []
    for date, date_dict in record_dict_new.items():
        if date != "all_dates":
            date_list.append(date)
            NPC_nums_list.append(date_dict["all_ips"]["NPC_nums"])
            image_nums_list.append(date_dict["all_ips"]["image_nums"])

    NPC_nums_update = gr.LinePlot(
        value=pd.DataFrame({"x": date_list, "y": NPC_nums_list}),
        x="x",
        y="y",
        overlay_point=True,
        tooltip=["x", "y"],
        title="NPC nums",
        width=1000,
        height=350,
    )
    image_nums_update = gr.LinePlot(
        value=pd.DataFrame({"x": date_list, "y": image_nums_list}),
        x="x",
        y="y",
        overlay_point=True,
        tooltip=["x", "y"],
        title="image nums",
        width=1000,
        height=350,
    )
    NPC_nums_txt = '\n'.join([f"all_NPC_nums: {record_dict_new['all_dates']['all_NPC_nums']}", f"all_chat_NPC_nums: {record_dict_new['all_dates']['all_chat_NPC_nums']}", f"all_wishwell_NPC_nums: {record_dict_new['all_dates']['all_wishwell_NPC_nums']}"])
    image_nums_txt = '\n'.join([f"all_image_nums: {record_dict_new['all_dates']['all_image_nums']}", f"all_chat_image_nums: {record_dict_new['all_dates']['all_chat_image_nums']}", f"all_wishwell_image_nums: {record_dict_new['all_dates']['all_wishwell_image_nums']}"])
    
    return NPC_nums_update, image_nums_update, NPC_nums_txt, image_nums_txt

def pipeline():
    # 0. 获取log
    log_file_paths = get_logs()

    # 1. 记录在json中
    record_dict_new = record_json(log_file_paths)

    # 2. 根据json画图
    NPC_nums_update, image_nums_update, NPC_nums_txt, image_nums_txt = generate_bar_chart(record_dict_new)

    # 3. 获取刷新时间
    recent_refresh_time = datetime.now()
    next_refresh_time = recent_refresh_time + timedelta(hours=refresh_hour)
    note_txt = f'This page is automatically refreshed every {refresh_hour} hours, you don\'t need and better not to refresh it manually, just keep this page.\nRecent refresh time: {recent_refresh_time.strftime("%Y-%m-%d %H:%M:%S")}\nNext refresh time: {next_refresh_time.strftime("%Y-%m-%d %H:%M:%S")}'
    
    return note_txt, NPC_nums_update, image_nums_update, NPC_nums_txt, image_nums_txt

def show_plot():
    with gr.Blocks() as show_plot_blocks:
        with gr.Column():
            note_txt = gr.Textbox("", label="note", interactive=False, lines=3)
            NPC_nums_plot = gr.LinePlot(show_label=False)
            NPC_nums_txt = gr.Textbox('', label="", interactive=False, lines=3)
            image_nums_plot = gr.LinePlot(show_label=False)
            image_nums_txt = gr.Textbox('', label="", interactive=False, lines=3)
            show_ = gr.Button("Show", visible=False)
    show_.click(
        fn=pipeline,
        inputs=[],
        outputs=[note_txt, NPC_nums_plot, image_nums_plot, NPC_nums_txt, image_nums_txt]
    )
    show_plot_blocks.load(
        fn=pipeline, 
        inputs=[], 
        outputs=[note_txt, NPC_nums_plot, image_nums_plot, NPC_nums_txt, image_nums_txt], 
        every=refresh_hour*3600
    )


if __name__ == "__main__":
    refresh_hour = 8
    server_port = 8000
    log_path = "/data/linky/chenyu.liu/linky_latest/as-loki/image_generate_offline_server/file_process/temp_files/log_files/launch_pipeline_auto_gradio_all.log"
    save_log_dir = "/data/linky/chenyu.liu/others/view_offline_gen_image_nums/logs"
    
    mode_info_dict = {
        "chat": {
            "group": 30,
            "imgs": 4,
            "deform_percent": 0.75
        },
        "wishwell": {
            "group": 30,
            "imgs": 8,
            "deform_percent": 0.75
        }
    }
    host_dict = {
        "0": {
            "public": "123.56.72.141",
            "private": "172.19.39.172"
        },
        "1": {
            "public": "123.56.72.135",
            "private": "172.19.39.177"
        },
        "2": {
            "public": "123.56.190.195",
            "private": "172.19.39.173"
        },
        "3": {
            "public": "8.147.115.70",
            "private": "172.19.39.164"
        },
        "4": {
            "public": "123.56.136.79",
            "private": "172.19.39.170"
        }
    }

    with gr.Blocks() as demo:
        gr.Markdown("""
                    <div style="display: inline">
                    <strong><em>view offline generate image nums</em></strong>
                    </div>
                    """)
        with gr.Tabs():
            with gr.TabItem("show plot") as tab_show_plot:
                show_plot()
                
    demo.queue().launch(server_port=server_port, server_name="0.0.0.0", share=True)
