import time
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QHBoxLayout, QMessageBox, QTextEdit, QProgressBar
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTextCodec
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import requests
import base64
import re
import os
import sys

class DownloadThread(QThread):
    update_progress = pyqtSignal(str)  # 更新下载进度信息的信号
    update_percentage = pyqtSignal(int)  # 更新下载进度百分比的信号
    update_search_progress = pyqtSignal(str)  # 更新检索进度信息的信号
    update_search_percentage = pyqtSignal(int)  # 更新检索进度百分比的信号

    def __init__(self, search_keyword, download_path):
        super().__init__()
        self.search_keyword = search_keyword
        self.download_path = download_path

    def run(self):
        driver_path = '/usr/local/bin/msedgedriver'#这里是你的edge驱动路径
        self.update_search_progress.emit(f" 检索中喵~  {self.search_keyword}")
        service = Service(driver_path)
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        driver = webdriver.Edge(service=service,options=options)
        driver.get("https://www.baidu.com")
        search_box = driver.find_element("id", "kw")
        search_box.send_keys(self.search_keyword)
        search_box.send_keys(Keys.RETURN)
        driver.implicitly_wait(10)
        current_url = driver.current_url
        driver.get(current_url)
        image_element = driver.find_element("link text", "图片")
        image_element.click()
        current_url = driver.current_url
        driver.get(current_url)
        for i in range(1000):  
            
            driver.execute_script("window.scrollBy(0, window.innerHeight)")
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            percentage = int((i + 1) / 1000 * 100)
            
            self.update_search_percentage.emit(percentage)  # 发射更新检索进度百分比的信号
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        images = soup.find_all('img')
        self.update_search_progress.emit(f"检索完成喵~ 已找到 {len(images)} 张图片，开始下载...")
        #等待1.5秒
        time.sleep(1.5)
        for idx, image in enumerate(images):
            src = image.get('src')
            if src:
                if src.startswith('http') or src.startswith('https'):
                    response = requests.get(src)
                    if response.status_code == 200:
                        with open(f'{self.download_path}/{self.search_keyword}_{idx}.jpg', 'wb') as f:
                            f.write(response.content)
                            self.update_progress.emit(f"已下载图片 {idx}")
                elif src.startswith('data:image'):
                    base64_data = re.search(r'base64,(.*)', src).group(1)
                    with open(f'{self.download_path}/{self.search_keyword}_{idx}.jpg', 'wb') as f:
                        f.write(base64.b64decode(base64_data))
                        self.update_progress.emit(f"已下载图片 {idx}")
            percentage = int((idx + 1) / len(images) * 100)
            self.update_percentage.emit(percentage)  # 发射更新下载进度百分比的信号
        driver.quit()
        self.update_progress.emit("下载完成！")
class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.setFixedHeight(650)
        self.setFixedWidth(500) 

        search_label = QLabel("搜索关键字:")
        layout.addWidget(search_label)

        self.search_line_edit = QLineEdit()
        layout.addWidget(self.search_line_edit)
        folder_label = QLabel("目标文件夹路径:")
        layout.addWidget(folder_label)
        
        folder_layout = QHBoxLayout()  

        self.folder_line_edit = QLineEdit()
        folder_layout.addWidget(self.folder_line_edit)

        browse_button = QPushButton("浏览...")
        folder_layout.addWidget(browse_button)
        browse_button.clicked.connect(self.browse_folder)
        layout.addLayout(folder_layout) 
        self.setLayout(layout)
        info_label = QLabel("使用说明：\n先输入要搜索图片的关键字，在选择要下载图片的目标路径，\n然后点击下载按钮开始下载图片")
        layout.addWidget(info_label)
        layout.addStretch(10)  

        # 添加保存按钮和下载按钮到同一行
        button_layout = QHBoxLayout()
        

        download_button = QPushButton("下载")
        button_layout.addWidget(download_button)        
        download_button.clicked.connect(self.download_files)
        save_button = QPushButton("保存记录")
        button_layout.addWidget(save_button)
        save_button.clicked.connect(self.save_record)
        layout.addLayout(button_layout)

        # 添加滚动窗口用来显示下载信息
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)  # 设置为只读
        layout.addWidget(self.log_text_edit)

        # 添加检索进度条
        self.search_progress_label = QLabel("检索进度:")
        layout.addWidget(self.search_progress_label)
        self.search_progress_bar = QProgressBar()
        layout.addWidget(self.search_progress_bar)

        # 添加下载进度条
        self.download_progress_label = QLabel("下载进度:")
        layout.addWidget(self.download_progress_label)
        self.download_progress_bar = QProgressBar()
        self.download_progress_bar.setStyleSheet(
            "QProgressBar::chunk { background-color: #00FF00; }"
        )
        self.download_progress_bar.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.download_progress_bar)

        # 在启动时加载记录
        self.load_record()
        # 当主窗口移动时，更新下载完成消息框的位置
        self.moveEvent = self.onMoveEvent
    def onMoveEvent(self, event):
        # 获取主窗口的当前位置
        main_window_rect = self.rect()
        main_window_center = main_window_rect.center()

        # 获取下载完成消息框的当前位置
        if hasattr(self, 'download_success_message_box'):
            download_message_box_rect = self.download_success_message_box.rect()
            download_message_box_center = download_message_box_rect.center()

            # 计算消息框应该移动的偏移量
            offset = main_window_center - download_message_box_center

            # 移动消息框到新位置
            self.download_success_message_box.move(self.download_success_message_box.pos() + offset)

        # 调用父类的移动事件处理函数
        super().moveEvent(event)


    def browse_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择目标文件夹", "", QFileDialog.ShowDirsOnly)
        if folder_path:
            self.folder_line_edit.setText(folder_path)
    # 在MyWidget类中添加一个方法来显示下载完成的消息
    def show_download_success_message(self):
        QMessageBox.information(self, "下载成功", "下载成功喵~", QMessageBox.Ok)

    # 不需要修改onMoveEvent方法，因为QMessageBox是模态的，不会常驻屏幕

    def download_files(self):
        search_keyword = self.search_line_edit.text()  
        download_path = self.folder_line_edit.text()  
        if(search_keyword==''):
            QMessageBox.information(self, "提示", "请输入搜索关键字")
            return
        if(download_path==''):
            QMessageBox.information(self, "提示", "请输入目标文件夹路径")
            return
        # 检查目标文件夹路径是否存在
        if not os.path.exists(download_path):
            QMessageBox.information(self, "提示", "目标文件夹路径不存在，请重新选择")
            return
         # 清空下载信息和进度条
        self.clear_progress_bar()# 清空进度条的值
        self.log_text_edit.clear()  # 清空下载信息
        self.download_thread = DownloadThread(search_keyword, download_path)
        self.download_thread.update_progress.connect(self.update_progress) 
        self.download_thread.update_percentage.connect(self.update_percentage)  # 连接更新下载进度百分比的信号
        self.download_thread.update_search_progress.connect(self.update_search_progress) 
        self.download_thread.update_search_percentage.connect(self.update_search_percentage)  # 连接更新检索进度百分比的信号
        self.download_thread.start()
        # 下载完成后显示消息框
        self.download_thread.finished.connect(self.show_download_success_message)

    def update_progress(self, msg):
        
        self.log_text_edit.append(msg)  # 更新下载信息
    def update_percentage(self, percentage): 
        self.show_download_value(percentage)
        if percentage < 51:  
             self.download_progress_bar.setStyleSheet(
            "QProgressBar { color: black; }"  # 设置默认的文本颜色为黑色
            "QProgressBar::chunk { background-color: #00FF00; color: black; }"  # 设置填充颜色为绿色，文本颜色为白色
            )
        else:
             self.download_progress_bar.setStyleSheet(
            "QProgressBar { color: white; }"  # 设置默认的文本颜色为黑色
            "QProgressBar::chunk { background-color: #00FF00; color: white; }"  # 设置填充颜色为绿色，文本颜色为白色
            )
        self.download_progress_bar.setValue(percentage)  # 更新下载进度条的值   
   
    def update_search_progress(self, msg):
        
        self.log_text_edit.append(msg)  # 更新检索信息

    def update_search_percentage(self, percentage):
        self.show_progress_value(percentage)
        self.search_progress_bar.setValue(percentage)  # 更新检索进度条的值
    def clear_progress_bar(self):
        # 清空进度条的值
        self.download_progress_bar.setValue(0)
        # 隐藏百分比文本
        self.download_progress_bar.setFormat("")
        # 清空进度条的值
        self.search_progress_bar.setValue(0)
        # 隐藏百分比文本
        self.search_progress_bar.setFormat("")
    def show_progress_value(self, value):
        # 设置百分比文本的格式，显示当前值
        self.search_progress_bar.setFormat(f"{value}%")
    def show_download_value(self, value):
        # 设置百分比文本的格式，显示当前值
        self.download_progress_bar.setFormat(f"{value}%")
    def save_record(self):
        search_keyword = self.search_line_edit.text()
        download_path = self.folder_line_edit.text()
        if search_keyword and download_path:
            with open("download_record.txt", "w") as f:
                f.write(f"搜索关键字：{search_keyword}\n")
                f.write(f"目标文件夹：{download_path}\n")
                QMessageBox.information(self, "提示", "记录已保存")
        else:
            QMessageBox.information(self, "提示", "请输入搜索关键字和目标文件夹路径")

    def load_record(self):
        try:
            with open("download_record.txt", "r") as f:
                lines = f.readlines()
                if len(lines) >= 2:
                    search_keyword = lines[0].split("：")[1].strip()
                    download_path = lines[1].split("：")[1].strip()
                    self.search_line_edit.setText(search_keyword)
                    self.folder_line_edit.setText(download_path)
        except FileNotFoundError:
            pass
if __name__ == "__main__":

    app = QApplication(sys.argv)
    codec = QTextCodec.codecForName("UTF-8")
    QTextCodec.setCodecForLocale(codec)
    app.setApplicationName("图片下载器")
    app.setWindowIcon(QIcon("图片下载器.png"))
    w = MyWidget()
    w.show()
    sys.exit(app.exec_())
