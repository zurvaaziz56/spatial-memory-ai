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

        grounded_context = ""
        grounded_urls = []
        if use_search_grounding.lower() == "true" and len(study_notes.strip()) < 40:
            try:
                search_resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"Extract 5 high-yield, technically accurate key terms and definitions for studying: {topic}. Be concise.",
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    )
                )
                grounded_context = search_resp.text or ""
                if search_resp.candidates and search_resp.candidates[0].grounding_metadata:
                    chunks = search_resp.candidates[0].grounding_metadata.grounding_chunks or []
                    for c in chunks[:3]:
                        if c.web and c.web.uri:
                            grounded_urls.append(c.web.title or c.web.uri)
            except Exception:
                grounded_context = ""

        prompt = f"""
You are a computational cognitive neuroscientist specializing in the Method of Loci (Spatial Memory Palaces) and Targeted Memory Reactivation (TMR).

Analyze this room image and identify exactly 5 distinct, well-spaced physical objects across the scene from left to right.
For each physical object:
1. Return its exact 2D bounding box `box_2d` in `[ymin, xmin, ymax, xmax]` format normalized from 0 to 1000.
2. Map one core concept from the study material below onto that physical object.
3. Create an unforgettable, bizarre, multisensory visual association (`sensory_mnemonic`) where the concept physically interacts with that specific object in the room.
4. Assign a distinct acoustic cue frequency (`acoustic_cue_hz`) between 220 and 660 Hz.
5. Write a Socratic recall question.

TARGET TOPIC: {topic}
USER STUDY MATERIAL: {study_notes}
GROUNDED KNOWLEDGE CONTEXT: {grounded_context}
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=MemoryPalaceResponse,
                temperature=0.4,
            )
        )

        result_data = json.loads(response.text)
        if grounded_urls:
            result_data["grounded_sources"] = grounded_urls
        elif not result_data.get("grounded_sources"):
            result_data["grounded_sources"] = ["Gemini 2.5 Flash Multimodal Spatial Engine"]

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
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RecallEvaluationResponse,
                temperature=0.2,
            )
        )
        return JSONResponse(content=json.loads(response.text))
    except Exception:
        user_low = req.user_answer.lower()
        term_low = req.concept_term.lower()
        passed = len(user_low) > 3 and (term_low[:4] in user_low or any(w in user_low for w in req.concept_definition.lower().split()[:5]))
        return JSONResponse(content={
            "score": 92 if passed else 35,
            "is_correct": passed,
            "feedback": f"Strong spatial retrieval at the {req.object_name}!" if passed else f"Visualize the bizarre action happening right on the {req.object_name} to trigger {req.concept_term}."
        })


app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")
