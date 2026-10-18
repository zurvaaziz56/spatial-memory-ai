import json
import os
from typing import List, Optional
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

app = FastAPI(title="Spatial Memory AI Engine")

def get_genai_client():
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key)
    return genai.Client()

class SpatialAnchor(BaseModel):
    id: int = Field(description="Sequential station number starting at 1")
    object_name: str = Field(description="Name of the physical object detected in the room photo")
    box_2d: List[int] = Field(description="2D bounding box [ymin, xmin, ymax, xmax] normalized 0 to 1000")
    concept_term: str = Field(description="The target term, concept, or formula to memorize")
    concept_definition: str = Field(description="Concise, accurate explanation or translation of the concept")
    sensory_mnemonic: str = Field(description="Vivid, bizarre, multisensory action scene physically linking the object_name to the concept_term")
    acoustic_cue_hz: int = Field(description="Distinct musical frequency in Hz between 220 and 660 for Targeted Memory Reactivation")
    socratic_question: str = Field(description="Active recall question that prompts the user to retrieve the concept using the spatial anchor")

class MemoryPalaceResponse(BaseModel):
    topic_summary: str
    cognitive_principle: str
    grounded_sources: List[str]
    anchors: List[SpatialAnchor]

class RecallEvaluationRequest(BaseModel):
    object_name: str
    concept_term: str
    concept_definition: str
    user_answer: str

class RecallEvaluationResponse(BaseModel):
    score: int = Field(description="Score from 0 to 100 based on semantic accuracy")
    is_correct: bool = Field(description="True if score is 70 or above")
    feedback: str = Field(description="1-sentence Socratic feedback reinforcing the spatial anchor")


GEMINI_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-3.8-flash",
]


@app.post("/api/generate-palace")
async def generate_palace(
    topic: str = Form(...),
    study_notes: Optional[str] = Form(""),
    use_search_grounding: Optional[str] = Form("true"),
    image: UploadFile = File(...)
):
    try:
        client = get_genai_client()
        image_bytes = await image.read()
        mime_type = image.content_type or "image/jpeg"

        grounded_urls = []
        grounded_links = []

        prompt = f"""
Analyze this room image and identify 5 distinct, well-spaced physical objects from left to right.
For each of the 5 objects:
1. Return its exact 2D bounding box `box_2d` in `[ymin, xmin, ymax, xmax]` format normalized from 0 to 1000.
2. Map one core concept from the topic below onto that physical object.
3. Write a concise, playful 1-sentence visual story (`sensory_mnemonic`) where the concept physically interacts with that specific object in the room.
4. Assign a distinct acoustic cue frequency (`acoustic_cue_hz`) between 220 and 660 Hz.
5. Write a clear 1-sentence Socratic recall question.

TARGET TOPIC: {topic}
USER STUDY MATERIAL: {study_notes}
"""

        last_err = None
        result_data = None
        for model_name in GEMINI_MODELS:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                        prompt
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=MemoryPalaceResponse,
                        temperature=0.35,
                    )
                )
                result_data = json.loads(response.text)
                break
            except Exception as err:
                last_err = err

        if result_data is None:
            raise last_err or RuntimeError("All Gemini models failed")

        result_data["grounded_links"] = grounded_links
        if grounded_urls:
            result_data["grounded_sources"] = grounded_urls
        elif not result_data.get("grounded_sources"):
            result_data["grounded_sources"] = ["Gemini Multimodal Spatial Engine"]

        return JSONResponse(content=result_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini Spatial Pipeline Error: {str(e)}")


@app.post("/api/evaluate-recall")
async def evaluate_recall(req: RecallEvaluationRequest):
    try:
        client = get_genai_client()
        prompt = f"""
Evaluate the learner's active recall response during a Method of Loci Socratic sprint.
Physical Room Anchor: {req.object_name}
Target Concept: {req.concept_term}
Target Definition: {req.concept_definition}
Learner's Response: {req.user_answer}

Grade semantically (paraphrased accurate understanding should score 85-100). If partially correct or wrong, give a brief 1-sentence Socratic cue referencing the physical anchor ({req.object_name}).
"""
        for model_name in GEMINI_MODELS:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=RecallEvaluationResponse,
                        temperature=0.2,
                    )
                )
                return JSONResponse(content=json.loads(response.text))
            except Exception:
                continue
        raise RuntimeError("Fallback to offline grader")
    except Exception:
        user_low = req.user_answer.lower()
        term_low = req.concept_term.lower()
        passed = len(user_low) > 3 and (term_low[:4] in user_low or any(w in user_low for w in req.concept_definition.lower().split()[:5]))
        return JSONResponse(content={
            "score": 92 if passed else 35,
            "is_correct": passed,
            "feedback": f"Strong spatial retrieval at the {req.object_name}!" if passed else f"Visualize the bizarre action happening right on the {req.object_name} to trigger {req.concept_term}."
        })


app.mount("/rooms", StaticFiles(directory="static/rooms"), name="rooms")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")
