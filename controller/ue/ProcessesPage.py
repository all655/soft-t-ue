import uuid

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout

from SharedState import SharedState
from Ue import Ue
from ChannelAgent import ChannelAgent
from Monitor import Monitor


class ProcessesPage(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ue_index = SharedState.ue_index
        layout = BoxLayout(orientation='vertical')
        self.monitor = Monitor()
        self.monitor.monitor_process("gnb", r'gnb -c')
        self.monitor.monitor_process("open5gs", r'open5gs-nrfd')
        self.monitor.monitor_process("metrics-server", r'/usr/local/bin/metrics-server')
        self.monitor.monitor_process("influxdb", r'influxd')
        self.monitor_labels = [Label(text=f"",
                                   font_name="./font/Ubuntu/Ubuntu-Regular.ttf",
                                   size_hint=(None, None),
                                   height=20,
                                   width=300,
                                   font_size="15sp",
                                   halign="left",
                                   pos_hint={"top": 1}) for _ in range(4)]
        label_container = GridLayout(cols=1, spacing=20)
        monitor_container = FloatLayout()
        for label in self.monitor_labels:
            label_container.add_widget(label)
        monitor_container.add_widget(label_container)
        self.add_widget(monitor_container)
        Clock.schedule_interval(lambda dt: self.update_monitor_label(), 1)
        self.process_container = BoxLayout(
            orientation="vertical", 
            size_hint_y=None,
        )
        self.process_container.bind(minimum_height=self.process_container.setter('height'))
        self.process_scroll = ScrollView()
        self.process_scroll.add_widget(self.process_container)
        layout.add_widget(self.process_scroll)


        add_ue_button = Button(
            text='Add Process',
            on_press=self.open_add_process_popup,
            background_color=[0,0.75,0.25,1],
            size_hint=(None,None),
            width=200,
            height=40,
            font_name="./font/Ubuntu/Ubuntu-Regular.ttf",
            pos_hint={"top": 1, "right": 1}
        )
        button_container = FloatLayout()
        layout.add_widget(add_ue_button)

        self.config_file = ""
        self.process_type = "clean"

        for ue in SharedState.process_list:
            self.add_process_log(ue["type"], ue["config"], ue["handle"])

        self.add_widget(layout)

    def update_monitor_label(self):
        count = 0
        for name, isRunning in self.monitor.monitor_list.items():
            if isRunning:
                self.monitor_labels[count].text = f"{name}: Running"
                self.monitor_labels[count].color = [0,1,1,1]
            else:
                self.monitor_labels[count].text = f"{name}: Down"
                self.monitor_labels[count].color = [1,0,0,1]
            count += 1


    def open_add_process_popup(self, instance):
        content = BoxLayout(orientation='vertical')
        self.config_label = Label(text="Selected file: None", font_name="./font/Ubuntu/Ubuntu-Regular.ttf")
        self.process_type_label = Label(text=f"Process Type: {self.process_type}", font_name="./font/Ubuntu/Ubuntu-Regular.ttf")

        cancel_button = Button(text="Cancel", size_hint_y=None, height=50)
        select_config_button = Button(text="Select config", size_hint_y=None, height=50)
        add_button = Button(text="Add", size_hint_y=None, height=50)

        process_type_spinner = Spinner(
            text='clean',
            values=('clean', 'tester', 'listener', 'jam_sequential', 'jam_random', 'jam_fixed'),
            size_hint=(None, None),
            size=(200, 44)
        )

        button_wrapper = BoxLayout(orientation='horizontal')

        content.add_widget(self.config_label)
        content.add_widget(select_config_button)
        content.add_widget(self.process_type_label)
        content.add_widget(process_type_spinner)
        button_wrapper.add_widget(cancel_button)
        button_wrapper.add_widget(add_button)
        content.add_widget(button_wrapper)

        self.popup = Popup(title='Add Process', content=content, size_hint=(0.5, 0.5))
        cancel_button.bind(on_press=self.popup.dismiss)
        add_button.bind(on_press=self.add_process)
        select_config_button.bind(on_press=self.open_select_file_popup)
        process_type_spinner.bind(text=self.set_process_type)
        self.popup.open()

    def open_select_file_popup(self, instance):
        content = BoxLayout(orientation='vertical')
        filechooser = FileChooserListView(path='/home/')
        button_layout = BoxLayout(size_hint_y=None, height=50)
        select_button = Button(text="Select", size_hint_y=None, height=50)
        cancel_button = Button(text="Cancel", size_hint_y=None, height=50)

        button_layout.add_widget(select_button)
        button_layout.add_widget(cancel_button)
        content.add_widget(filechooser)
        content.add_widget(button_layout)

        popup = Popup(title='Choose a File', content=content, size_hint=(0.9, 0.9))

        select_button.bind(on_press=lambda x: self.select_file(filechooser, popup))
        cancel_button.bind(on_press=popup.dismiss)

        popup.open()

    def select_file(self, filechooser, popup):
        selected = filechooser.selection
        if selected:
            self.config_file = selected[0]
            self.config_label.text = f'Selected file: {selected[0]}'
        popup.dismiss()

    def set_process_type(self, spinner, text):
        self.process_type_label.text = f'Process type: {text}'
        self.process_type = text

    def add_process(self, instance):
        self.popup.dismiss()
        if self.process_type == "clean" or self.process_type == "tester":
            new_ue = Ue(self.ue_index)
            new_ue.start([self.config_file] + SharedState.attack_args if self.process_type == "tester" else [])

            SharedState.process_list.append({
                'id': str(uuid.uuid4()),
                'type': self.process_type,
                'config': self.config_file + ' '.join(SharedState.attack_args),
                'handle': new_ue,
                'index': self.ue_index
            })

            self.add_process_log(self.process_type, self.config_file + ' '.join(SharedState.attack_args), new_ue)
            self.ue_index += 1

        elif self.process_type == "listener" or self.process_type == "jam_sequential" or self.process_type == "jam_random" or self.process_type == "jam_fixed":
            new_channel = ChannelAgent()
            new_channel.start(self.config_file)

            SharedState.process_list.append({
                'id': str(uuid.uuid4()),
                'type': self.process_type,
                'config': self.config_file,
                'handle': new_channel,
                'index': 0
            })

            self.add_process_log(self.process_type, self.config_file, new_channel)


        self.config_file = ""
        self.process_type = "clean"

    def collect_logs(self, label_ref, ue_ref, log_ref, title_ref):
        label_ref.text = ue_ref.output
        if not ue_ref.isRunning:
            title_ref.color = [1,0,0,1]
        elif not ue_ref.isConnected:
            title_ref.color = [1,1,0,1]
        else:
            title_ref.color = [0,1,0,1]
        log_ref.scroll_y = 0

    def add_process_log(self, ue_type, config, handle):
        log_view = GridLayout(
            cols=1,
            spacing=60,
            size_hint_y=None,
            height=700
        )
        new_process_text = Label(
            text="",
            halign="left",
            size_hint=(1,None),
            text_size=(None,None),
            font_size="25sp",
            padding=[10,20,10,20],
            font_name="./font/Ubuntu_Mono/UbuntuMono-Regular.ttf"
        )

        content_label = Label(
            text="",
            font_size="30sp",
            padding=[10,20,10,20],
            color=[1,1,0,1],
            font_name="./font/Ubuntu_Mono/UbuntuMono-Regular.ttf"
        )

        if ue_type == "clean" or ue_type == "tester":
            new_process_text.text = f"starting UE ({ue_type})..."
            content_label.text =  f"sudo srsue {config}"
        else:
            new_process_text.text = ue_type
            content_label.text = f"sudo uuagent {config}"


        Clock.schedule_interval(lambda dt: self.collect_logs(new_process_text, handle, log_view, content_label), 1)
        log_view.add_widget(content_label)
        log_view.add_widget(new_process_text)
        self.process_container.add_widget(log_view)
