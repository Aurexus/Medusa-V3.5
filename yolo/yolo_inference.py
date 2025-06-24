from ultralytics import YOLO
import cv2
import os

# Load the YOLO model
model = YOLO('yolo/best.pt')  # Path to your trained model

def run_yolo_inference(image_path):
    """
    Perform inference using the YOLO model.
    Args:
        image_path (str): Path to the input image.
    Returns:
        dict: Inference results including image with detections and raw data.
    """
    # Run inference
    results = model(image_path)

    # Load the image
    image = cv2.imread(image_path)

    # Draw detections
    for box in results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
        confidence = box.conf.item()
        class_id = int(box.cls)

        # Draw bounding box and label
        label = f"Class {class_id} ({confidence:.2f})"
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(image, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Save the processed image
    output_path = os.path.join("static/results", os.path.basename(image_path))
    cv2.imwrite(output_path, image)

    # Return results
    return {
        "image_path": output_path,
        "detections": [
            {
                "class_id": int(box.cls),
                "confidence": box.conf.item(),
                "bbox": box.xyxy[0].cpu().numpy().tolist(),
            }
            for box in results[0].boxes
        ],
    }
