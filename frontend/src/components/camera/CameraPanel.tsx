import { Camera, Play, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { getErrorMessage } from "@/lib/utils";

interface CameraPanelProps {
  onReady: (capture: (() => string | null) | null) => void;
  autoStart?: boolean;
  hideControls?: boolean;
  idleText?: string;
}

export function CameraPanel({ onReady, autoStart = false, hideControls = false, idleText }: CameraPanelProps) {
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState("");
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const onReadyRef = useRef(onReady);
  onReadyRef.current = onReady;

  const captureFrame = () => {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0 || video.videoHeight === 0) return null;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) return null;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.88);
  };

  const start = async () => {
    if (streamRef.current) return;
    try {
      setMessage("");
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: "user"
        },
        audio: false
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setRunning(true);
      onReadyRef.current(captureFrame);
    } catch (error) {
      setMessage(getErrorMessage(error, "Browser camera permission was denied."));
      setRunning(false);
      onReadyRef.current(null);
    }
  };

  const stop = () => {
    setRunning(false);
    onReadyRef.current(null);
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
  };

  useEffect(() => () => stop(), []);

  useEffect(() => {
    if (autoStart) {
      void start();
      return;
    }
    stop();
  }, [autoStart]);

  return (
    <div className="camera-panel">
      <div className="camera-frame">
        <video ref={videoRef} playsInline muted className={running ? "camera-video active" : "camera-video"} />
        {!running && (
          <div className="camera-idle">
            <Camera size={38} />
            <strong>Camera is off</strong>
            <span>{message || idleText || "Start it only when registering faces or taking attendance."}</span>
          </div>
        )}
      </div>
      {!hideControls && (
        <div className="camera-actions">
          <button className="secondary-button" onClick={start}>
            <Play size={18} />
            Start Camera
          </button>
          <button className="danger-button" onClick={stop} disabled={!running}>
            <Square size={18} />
            Stop
          </button>
        </div>
      )}
    </div>
  );
}
