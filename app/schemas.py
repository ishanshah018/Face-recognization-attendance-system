from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


def _clean(value: str) -> str:
    return " ".join(value.strip().split())


class StudentIn(BaseModel):
    id: int | None = Field(default=None, ge=1)
    roll_number: str = Field(min_length=1, max_length=40)
    full_name: str = Field(min_length=2, max_length=120)
    age: int | None = Field(default=None, ge=15, le=80)
    email: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    department: str = Field(default="", max_length=80)
    program: str = Field(default="", max_length=80)
    academic_year: str = Field(default="", max_length=40)
    semester: str = Field(default="", max_length=30)
    section: str = Field(default="", max_length=20)

    @field_validator("roll_number", "full_name", "department", "program", "academic_year", "semester", "section")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        return _clean(value)

    @field_validator("email", "phone")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = _clean(value)
        return cleaned or None


class CaptureRequest(BaseModel):
    student: StudentIn
    sample_target: int = Field(default=35, ge=15, le=80)


class FrameCaptureRequest(CaptureRequest):
    image_data: str = Field(min_length=100)


class FrameScanRequest(BaseModel):
    image_data: str = Field(min_length=100)


class AttendanceSessionIn(BaseModel):
    attendance_date: date | None = None
    title: str = Field(min_length=2, max_length=120)
    department: str = Field(default="", max_length=80)
    program: str = Field(default="", max_length=80)
    academic_year: str = Field(default="", max_length=40)
    semester: str = Field(default="", max_length=30)
    section: str = Field(default="", max_length=20)

    @field_validator("title", "department", "program", "academic_year", "semester", "section")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return _clean(value)


class ReportFilters(BaseModel):
    preset: Literal["today", "this_month", "last_month", "this_year", "last_year", "custom"]
    start_date: date | None = None
    end_date: date | None = None
    department: str = ""
    program: str = ""
    academic_year: str = ""
    semester: str = ""
    section: str = ""

    @model_validator(mode="after")
    def validate_custom_range(self) -> "ReportFilters":
        if self.preset == "custom":
            if not self.start_date or not self.end_date:
                raise ValueError("Custom range needs both start and end dates.")
            if self.start_date > self.end_date:
                raise ValueError("Start date cannot be after end date.")
        return self
