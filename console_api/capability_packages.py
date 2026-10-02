"""Thin adapters; core owns provenance and eligibility policy."""
from fastapi import APIRouter, Request
from academic_os.curriculum_ingestion.models import SelectedCurriculumTarget
from academic_os.curriculum_ingestion.core import IngestionError
from academic_os.curriculum_capability.models import AcademicCapabilityPackage, PackageReceipt

router = APIRouter()


@router.post('/api/curriculum-targets/{target_id}/capability-package', response_model=PackageReceipt, status_code=201)
def construct(target_id: str, body: SelectedCurriculumTarget, request: Request):
    if body.target_id != target_id:
        raise IngestionError('STALE_SELECTION', 'URL and selected target identity disagree.')
    service = request.app.state.capability_packages
    return service.persist(service.build_capability_package(body))


@router.get('/api/capability-packages/{package_id}', response_model=AcademicCapabilityPackage)
def read(package_id: str, request: Request):
    return request.app.state.capability_packages.read_capability_package(package_id)
