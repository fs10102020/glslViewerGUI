import re

_VALID_NAME_RE = re.compile(r"^[A-Za-z_][\w]*$")

def _validate_no_commas(value: str, label: str = "value") -> str:
    if "," in value:
        raise ValueError(
            f"{label} contains a comma, which glslViewer cannot parse: {value!r}"
        )
    return value

def _validate_name(name: str, label: str = "name") -> str:
    _validate_no_commas(name, label)
    if not _VALID_NAME_RE.match(name):
        raise ValueError(f"Invalid {label}: {name!r}")
    return name

def csv_command(*parts: object) -> str:
    result = ",".join(str(p) for p in parts)
    return result

def csv_command_safe(*parts: object) -> str:
    return csv_command(*parts)

def build_define(name: str, value: str = "") -> str:
    _validate_name(name, "define name")
    _validate_no_commas(value, "define value")
    if value:
        return csv_command("define", name, value)
    return csv_command("define", name)

def build_undefine(name: str) -> str:
    _validate_name(name, "undefine name")
    return csv_command("undefine", name)

def build_uniform(name: str, value) -> str:
    _validate_name(name, "uniform name")
    if isinstance(value, (list, tuple)):
        parts = ",".join(str(v) for v in value)
        return f"{name},{parts}"
    return f"{name},{value}"

def build_texture(name: str, path: str, flip: bool = False) -> str:
    _validate_name(name, "texture name")
    _validate_no_commas(path, "texture path")
    if flip:
        return csv_command("texture", name, path, "flip")
    return csv_command("texture", name, path)

def build_stream_texture(name: str, path: str, webcam: bool = False, flip: bool = False) -> str:
    _validate_name(name, "stream name")
    _validate_no_commas(path, "stream path")
    parts = ["stream_texture", name, path]
    # glslViewer's fourth argument is either "webcam" or "flip", never both.
    if webcam:
        parts.append("webcam")
    elif flip:
        parts.append("flip")
    return csv_command(*parts)

def build_audio_texture(name: str, device_id: str = "-1") -> str:
    _validate_name(name, "audio name")
    return csv_command("audio_texture", name, device_id)

def build_cubemap_load(name: str, path: str, show: bool = False) -> str:
    _validate_name(name, "cubemap name")
    _validate_no_commas(path, "cubemap path")
    if show:
        return csv_command("cubemap_load", name, path, "show")
    return csv_command("cubemap_load", name, path)

def build_skybox(path: str) -> str:
    _validate_no_commas(path, "skybox path")
    return csv_command("skybox", path)

def build_environment(path: str) -> str:
    _validate_no_commas(path, "environment path")
    return csv_command("environment", path)

def build_sequence_uniform(name: str, csv_path: str) -> str:
    _validate_name(name, "sequence uniform name")
    _validate_no_commas(csv_path, "CSV path")
    return csv_command("sequence_uniform", name, csv_path)

def build_camera_sequence(csv_path: str) -> str:
    _validate_no_commas(csv_path, "CSV path")
    return csv_command("camera_sequence", csv_path)

def build_include_path(folder: str) -> str:
    _validate_no_commas(folder, "include path")
    return csv_command("include_path", folder)

def build_load_model(path: str) -> str:
    _validate_no_commas(path, "model path")
    return csv_command("load_model", path)

def build_sequence(prefix: str, from_sec: float, to_sec: float, fps: float = 24.0) -> str:
    if prefix:
        _validate_no_commas(prefix, "sequence prefix")
        return csv_command("sequence", prefix, from_sec, to_sec, fps)
    return csv_command("sequence", from_sec, to_sec, fps)

def build_secs(prefix: str, from_sec: float, to_sec: float, fps: float = 24.0) -> str:
    if prefix:
        _validate_no_commas(prefix, "sequence prefix")
        return csv_command("secs", prefix, from_sec, to_sec, fps)
    return csv_command("secs", from_sec, to_sec, fps)

def build_frames(prefix: str, from_frame: int, to_frame: int, fps: float = 24.0) -> str:
    if prefix:
        _validate_no_commas(prefix, "sequence prefix")
        return csv_command("frames", prefix, from_frame, to_frame, fps)
    return csv_command("frames", from_frame, to_frame, fps)

def build_record(path: str, from_sec: float, to_sec: float, fps: float = 24.0) -> str:
    _validate_no_commas(path, "record path")
    return csv_command("record", path, from_sec, to_sec, fps)

def build_screenshot(path: str) -> str:
    _validate_no_commas(path, "screenshot path")
    return csv_command("screenshot", path)

def build_plot(mode: str) -> str:
    return csv_command("plot", mode)

def build_debug(on: bool) -> str:
    return csv_command("debug", "on" if on else "off")

def build_error_screen(on: bool) -> str:
    return csv_command("error_screen", "on" if on else "off")

def build_cursor(on: bool) -> str:
    return csv_command("cursor", "on" if on else "off")

def build_vsync(on: bool) -> str:
    return csv_command("vsync", "on" if on else "off")

def build_full_fps(on: bool) -> str:
    return csv_command("fullFps", "on" if on else "off")

def build_fps(value: int) -> str:
    return csv_command("fps", value)

def build_reset() -> str:
    return csv_command("reset")

def build_camera_distance(dist: float) -> str:
    return csv_command("camera_distance", dist)

def build_camera_fov(fov: int) -> str:
    return csv_command("camera_fov", fov)

def build_camera_type(proj: str) -> str:
    return csv_command("camera_type", proj)

def build_camera_position(x: float, y: float, z: float) -> str:
    return csv_command("camera_position", x, y, z)

def build_camera_look_at(x: float, y: float, z: float) -> str:
    return csv_command("camera_look_at", x, y, z)

def build_camera_move(dx: float, dy: float, dz: float) -> str:
    return csv_command("camera_move", dx, dy, dz)

def build_camera_exposure(aperture: float, shutter: float, sensitivity: float) -> str:
    return csv_command("camera_exposure", aperture, shutter, sensitivity)

def build_light_position(x: float, y: float, z: float) -> str:
    return csv_command("light_position", x, y, z)

def build_light_color(r: float, g: float, b: float) -> str:
    return csv_command("light_color", r, g, b)

def build_light_falloff(value: float) -> str:
    return csv_command("light_falloff", value)

def build_light_intensity(value: float) -> str:
    return csv_command("light_intensity", value)

def build_sun_elevation(degrees: float) -> str:
    return csv_command("sun_elevation", degrees)

def build_sun_azimuth(degrees: float) -> str:
    return csv_command("sun_azimuth", degrees)

def build_sky_turbidity(value: float) -> str:
    return csv_command("sky_turbidity", value)

def build_stream_play(name: str) -> str:
    return csv_command("stream", name, "play")

def build_stream_stop(name: str) -> str:
    return csv_command("stream", name, "stop")

def build_stream_restart(name: str) -> str:
    return csv_command("stream", name, "restart")

def build_stream_speed(name: str, speed: float) -> str:
    return csv_command("stream", name, "speed", speed)

def build_stream_time(name: str, time: float) -> str:
    return csv_command("stream", name, "time", time)

def build_stream_pct(name: str, pct: float) -> str:
    return csv_command("stream", name, "pct", pct)

def build_streams_play() -> str:
    return csv_command("streams", "play")

def build_streams_stop() -> str:
    return csv_command("streams", "stop")

def build_streams_restart() -> str:
    return csv_command("streams", "restart")

def build_streams_speed(speed: float) -> str:
    return csv_command("streams", "speed", speed)

def build_streams_time(time: float) -> str:
    return csv_command("streams", "time", time)

def build_streams_pct(pct: float) -> str:
    return csv_command("streams", "pct", pct)

def build_streams_frame(frame: int) -> str:
    return csv_command("streams", "frame", frame)

def build_streams_prevs(prevs: int) -> str:
    return csv_command("streams", "prevs", prevs)

def build_buffers(on: bool) -> str:
    return csv_command("buffers", "on" if on else "off")

def build_textures_display(on: bool) -> str:
    return csv_command("textures", "on" if on else "off")

def build_floor(on: bool) -> str:
    return csv_command("floor", "on" if on else "off")

def build_grid(on: bool) -> str:
    return csv_command("grid", "on" if on else "off")

def build_axis(on: bool) -> str:
    return csv_command("axis", "on" if on else "off")

def build_bboxes(on: bool) -> str:
    return csv_command("bboxes", "on" if on else "off")

def build_models_clear() -> str:
    return csv_command("models", "clear")

def build_generate_sdf(padding: float = 0.01) -> str:
    return csv_command("generate_sdf", padding)

def build_track_start() -> str:
    return csv_command("track", "on")

def build_track_stop() -> str:
    return csv_command("track", "off")

def build_track_average(label: str = "") -> str:
    if label:
        return csv_command("track", "average", label)
    return csv_command("track", "average")

def build_track_samples(label: str = "") -> str:
    if label:
        return csv_command("track", "samples", label)
    return csv_command("track", "samples")

def build_track_framerate() -> str:
    return csv_command("track", "framerate")

def build_cubemap_toggle() -> str:
    return csv_command("cubemap", "toggle")

def build_cubemap_sh() -> str:
    return csv_command("cubemap", "sh")

def build_sky_toggle() -> str:
    return csv_command("sky", "toggle")

def build_origin(x: float, y: float, z: float) -> str:
    return csv_command("origin", x, y, z)

def build_blend(mode: str) -> str:
    return csv_command("blend", mode)

def build_depth_test(on: bool) -> str:
    return csv_command("depth_test", "on" if on else "off")

def build_culling(mode: str) -> str:
    return csv_command("culling", mode)

def build_dynamic_shadows(on: bool) -> str:
    return csv_command("dynamic_shadows", "on" if on else "off")

def build_floor_color(r: float, g: float, b: float) -> str:
    return csv_command("floor_color", r, g, b)

def build_model_position(name: str, x: float, y: float, z: float) -> str:
    return csv_command("model", name, x, y, z)

def build_update() -> str:
    return csv_command("update")

def build_mouse_capture() -> str:
    return csv_command("mouse", "capture")

def build_reload() -> str:
    return csv_command("reload")

def build_reload_all() -> str:
    return csv_command("reload", "all")

def build_reload_file(path: str) -> str:
    _validate_no_commas(path, "file path")
    return csv_command("reload", path)

def build_update() -> str:
    return csv_command("update")

def build_help(cmd: str = "") -> str:
    if cmd:
        _validate_no_commas(cmd, "command")
        return csv_command("help", cmd)
    return csv_command("help")

def build_about() -> str:
    return csv_command("about")

def build_exit() -> str:
    return csv_command("exit")

def build_wait(seconds: float) -> str:
    return csv_command("wait", seconds)

def build_camera_list() -> str:
    return csv_command("camera", "list")

def build_camera_default() -> str:
    return csv_command("camera", "default")

def build_camera_name(name: str) -> str:
    _validate_name(name, "camera name")
    return csv_command("camera", name)

def build_lights() -> str:
    return csv_command("lights")

def build_textures_list() -> str:
    return csv_command("textures", "list")

def build_buffer(index: int, on: bool) -> str:
    return csv_command("buffers", index, "on" if on else "off")

def build_cubemaps() -> str:
    return csv_command("cubemaps")

def build_model(name: str) -> str:
    _validate_name(name, "model name")
    return csv_command("model", name)

def build_plane(resolution: str = "") -> str:
    if resolution:
        return csv_command("plane", resolution)
    return csv_command("plane")

def build_pcl_plane(resolution: str = "") -> str:
    if resolution:
        return csv_command("pcl_plane", resolution)
    return csv_command("pcl_plane")

def build_sphere(resolution: str = "") -> str:
    if resolution:
        return csv_command("sphere", resolution)
    return csv_command("sphere")

def build_pcl_sphere(resolution: str = "") -> str:
    if resolution:
        return csv_command("pcl_sphere", resolution)
    return csv_command("pcl_sphere")

def build_icosphere(resolution: str = "") -> str:
    if resolution:
        return csv_command("icosphere", resolution)
    return csv_command("icosphere")

def build_cylinder(res_radius: str = "", res_height: str = "", cap: str = "") -> str:
    parts = ["cylinder"]
    if res_radius:
        parts.append(res_radius)
        if res_height:
            parts.append(res_height)
            if cap:
                parts.append(cap)
    return csv_command(*parts)

def build_max_mem_in_queue(bytes_val: int) -> str:
    return csv_command("max_mem_in_queue", bytes_val)
