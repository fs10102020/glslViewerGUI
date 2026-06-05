import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QGroupBox, QLineEdit,
    QFileDialog, QListWidget, QMessageBox, QCheckBox,
)
from session_config import AssetSpec


class AssetsPanel(QWidget):
    asset_added = Signal(object)
    asset_refresh_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AssetsPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        tex_group = QGroupBox("Image / Video Texture")
        tex_form = QVBoxLayout(tex_group)

        tex_name_row = QHBoxLayout()
        tex_name_row.addWidget(QLabel("Uniform:"))
        self._tex_name = QLineEdit()
        self._tex_name.setPlaceholderText("u_tex0")
        tex_name_row.addWidget(self._tex_name)
        tex_form.addLayout(tex_name_row)

        tex_path_row = QHBoxLayout()
        tex_path_row.addWidget(QLabel("Path/URL:"))
        self._tex_path = QLineEdit()
        tex_path_row.addWidget(self._tex_path)
        browse_btn = QPushButton("Browse")
        browse_btn.setMaximumWidth(80)
        browse_btn.clicked.connect(self._on_browse_texture)
        tex_path_row.addWidget(browse_btn)
        tex_form.addLayout(tex_path_row)

        tex_opts = QHBoxLayout()
        self._tex_stream = QCheckBox("Video/Stream")
        self._tex_webcam = QCheckBox("Webcam")
        self._tex_flip = QCheckBox("Flip")
        tex_opts.addWidget(self._tex_stream)
        tex_opts.addWidget(self._tex_webcam)
        tex_opts.addWidget(self._tex_flip)
        tex_form.addLayout(tex_opts)

        tex_btn = QPushButton("Load Texture")
        tex_btn.setMinimumHeight(28)
        tex_btn.clicked.connect(self._on_load_texture)
        tex_form.addWidget(tex_btn)
        layout.addWidget(tex_group)

        audio_group = QGroupBox("Audio Texture")
        audio_form = QVBoxLayout(audio_group)
        aud_name_row = QHBoxLayout()
        aud_name_row.addWidget(QLabel("Uniform:"))
        self._audio_name = QLineEdit()
        self._audio_name.setPlaceholderText("u_audio0")
        aud_name_row.addWidget(self._audio_name)
        audio_form.addLayout(aud_name_row)
        aud_row = QHBoxLayout()
        aud_row.addWidget(QLabel("Device ID:"))
        self._audio_dev = QLineEdit()
        self._audio_dev.setPlaceholderText("-1 (default)")
        aud_row.addWidget(self._audio_dev)
        audio_form.addLayout(aud_row)
        aud_btn = QPushButton("Load Audio")
        aud_btn.setMinimumHeight(28)
        aud_btn.clicked.connect(self._on_load_audio)
        audio_form.addWidget(aud_btn)
        layout.addWidget(audio_group)

        env_group = QGroupBox("Cubemap / Sky / Environment")
        env_form = QVBoxLayout(env_group)
        env_row = QHBoxLayout()
        env_row.addWidget(QLabel("Path:"))
        self._env_path = QLineEdit()
        env_row.addWidget(self._env_path)
        env_browse = QPushButton("Browse")
        env_browse.setMaximumWidth(80)
        env_browse.clicked.connect(self._on_browse_hdr)
        env_row.addWidget(env_browse)
        env_form.addLayout(env_row)
        env_btns = QHBoxLayout()
        sky_btn = QPushButton("Load Skybox")
        sky_btn.setMinimumHeight(28)
        sky_btn.clicked.connect(self._on_load_skybox)
        env_btn = QPushButton("Load Environment")
        env_btn.setMinimumHeight(28)
        env_btn.clicked.connect(self._on_load_environment)
        env_btns.addWidget(sky_btn)
        env_btns.addWidget(env_btn)
        env_form.addLayout(env_btns)
        layout.addWidget(env_group)

        model_group = QGroupBox("3D Model / Geometry")
        model_form = QVBoxLayout(model_group)
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Path:"))
        self._model_path = QLineEdit()
        model_row.addWidget(self._model_path)
        model_browse = QPushButton("Browse")
        model_browse.setMaximumWidth(80)
        model_browse.clicked.connect(self._on_browse_model)
        model_row.addWidget(model_browse)
        model_form.addLayout(model_row)
        model_btn = QPushButton("Load Model")
        model_btn.setMinimumHeight(28)
        model_btn.clicked.connect(self._on_load_model)
        model_form.addWidget(model_btn)
        layout.addWidget(model_group)

        misc_group = QGroupBox("CSV Sequences")
        misc_form = QVBoxLayout(misc_group)
        csv_name_row = QHBoxLayout()
        csv_name_row.addWidget(QLabel("Uniform:"))
        self._csv_name = QLineEdit()
        self._csv_name.setPlaceholderText("u_values")
        csv_name_row.addWidget(self._csv_name)
        misc_form.addLayout(csv_name_row)
        csv_row = QHBoxLayout()
        csv_row.addWidget(QLabel("CSV:"))
        self._csv_path = QLineEdit()
        csv_row.addWidget(self._csv_path)
        csv_browse = QPushButton("Browse")
        csv_browse.clicked.connect(self._on_browse_csv)
        csv_row.addWidget(csv_browse)
        misc_form.addLayout(csv_row)
        csv_btn = QPushButton("Load Sequence")
        csv_btn.setMinimumHeight(28)
        csv_btn.clicked.connect(self._on_load_sequence)
        misc_form.addWidget(csv_btn)
        cam_seq_btn = QPushButton("Load Camera Sequence")
        cam_seq_btn.setMinimumHeight(28)
        cam_seq_btn.clicked.connect(self._on_load_camera_seq)
        misc_form.addWidget(cam_seq_btn)
        layout.addWidget(misc_group)

        refresh_row = QHBoxLayout()
        for label, cmd in [
            ("Textures", "textures,list"),
            ("Streams", "streams"),
            ("Cubemaps", "cubemaps"),
            ("Files", "files"),
        ]:
            btn = QPushButton(f"Refresh {label}")
            btn.setMaximumWidth(100)
            btn.clicked.connect(lambda checked=False, _c=cmd: self.asset_refresh_requested.emit(_c))
            refresh_row.addWidget(btn)
        refresh_row.addStretch()
        layout.addLayout(refresh_row)

        layout.addStretch()

    def _on_browse_texture(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Texture",
            "", "Images/Videos (*.png *.jpg *.jpeg *.bmp *.gif *.hdr *.exr *.tga *.psd *.mp4 *.mov *.mkv *.mpg *.mpeg *.h264);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if path:
            self._tex_path.setText(path)

    def _on_browse_hdr(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select HDR Cubemap",
            "", "HDR Images (*.hdr *.exr);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if path:
            self._env_path.setText(path)

    def _on_browse_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select 3D Model",
            "", "3D Models (*.ply *.obj *.stl *.glb *.gltf *.splat);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if path:
            self._model_path.setText(path)

    def _on_browse_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV", "", "CSV Files (*.csv);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if path:
            self._csv_path.setText(path)

    def _on_load_texture(self) -> None:
        name = self._tex_name.text().strip() or "u_tex0"
        path = self._tex_path.text().strip()
        if not path:
            return
        if self._tex_webcam.isChecked():
            spec = AssetSpec(kind="video", name=name, path=path, options={"webcam": True, "flip": self._tex_flip.isChecked()})
        elif self._tex_stream.isChecked():
            spec = AssetSpec(kind="video", name=name, path=path, options={"flip": self._tex_flip.isChecked()})
        else:
            spec = AssetSpec(kind="image", name=name, path=path, options={"flip": self._tex_flip.isChecked()})
        self.asset_added.emit(spec)

    def _on_load_audio(self) -> None:
        name = self._audio_name.text().strip() or "u_audio0"
        device = self._audio_dev.text().strip() or "-1"
        spec = AssetSpec(kind="audio", name=name, options={"device": device})
        self.asset_added.emit(spec)

    def _on_load_skybox(self) -> None:
        path = self._env_path.text().strip()
        if not path:
            return
        spec = AssetSpec(kind="skybox", path=path)
        self.asset_added.emit(spec)

    def _on_load_environment(self) -> None:
        path = self._env_path.text().strip()
        if not path:
            return
        spec = AssetSpec(kind="environment", path=path)
        self.asset_added.emit(spec)

    def _on_load_model(self) -> None:
        path = self._model_path.text().strip()
        if not path:
            return
        spec = AssetSpec(kind="model", path=path)
        self.asset_added.emit(spec)

    def _on_load_sequence(self) -> None:
        name = self._csv_name.text().strip()
        path = self._csv_path.text().strip()
        if not name or not path:
            return
        spec = AssetSpec(kind="sequence", name=name, path=path)
        self.asset_added.emit(spec)

    def _on_load_camera_seq(self) -> None:
        path = self._csv_path.text().strip()
        if not path:
            return
        spec = AssetSpec(kind="camera_sequence", path=path)
        self.asset_added.emit(spec)
