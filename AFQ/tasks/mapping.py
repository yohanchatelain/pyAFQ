import nibabel as nib
import os.path as op
import os
import numpy as np
import logging

import pimms
from AFQ.tasks.decorators import as_file
from AFQ.tasks.utils import get_fname, with_name
import AFQ.data as afd
import AFQ.utils.volume as auv
from AFQ.definitions.mapping import SynMap
from AFQ.definitions.utils import Definition

from dipy.io.streamline import load_tractogram
from dipy.io.stateful_tractogram import Space


logger = logging.getLogger('AFQ.api.mapping')


@pimms.calc("b0_warped_file")
@as_file('_b0_in_MNI.nii.gz')
def export_registered_b0(subses_dict, data_imap, mapping):
    """
    full path to a nifti file containing
    b0 transformed to template space
    """
    mean_b0 = nib.load(data_imap["b0_file"]).get_fdata()
    warped_b0 = mapping.transform(mean_b0)
    warped_b0 = nib.Nifti1Image(warped_b0, data_imap["reg_template"].affine)
    return warped_b0, dict(b0InSubject=data_imap["b0_file"])


@pimms.calc("template_xform_file")
@as_file('_template_xform.nii.gz')
def template_xform(subses_dict, dwi_affine, mapping, data_imap):
    """
    full path to a nifti file containing
    registration template transformed to subject space
    """
    template_xform = mapping.transform_inverse(
        data_imap["reg_template"].get_fdata())
    template_xform = nib.Nifti1Image(template_xform, dwi_affine)
    return template_xform, dict()


@pimms.calc("rois_file")
def export_rois(subses_dict, data_imap, mapping, dwi_affine):
    """
    dictionary of full paths to Nifti1Image files of ROIs
    transformed to subject space
    """
    bundle_dict = data_imap["bundle_dict"]
    rois_dir = op.join(subses_dict['results_dir'], 'ROIs')
    os.makedirs(rois_dir, exist_ok=True)
    roi_files = {}
    for bundle in bundle_dict:
        roi_files[bundle] = []
        for ii, roi in enumerate(bundle_dict[bundle]['ROIs']):
            if bundle_dict[bundle]['rules'][ii]:
                inclusion = 'include'
            else:
                inclusion = 'exclude'

            fname = op.split(
                get_fname(
                    subses_dict,
                    f'_desc-ROI-{bundle}-{ii + 1}-{inclusion}.nii.gz'))

            fname = op.join(rois_dir, fname[1])
            if not op.exists(fname):
                warped_roi = auv.transform_inverse_roi(
                    roi,
                    mapping,
                    bundle_name=bundle)

                # Cast to float32, so that it can be read in by MI-Brain:
                logger.info(f"Saving {fname}")
                nib.save(
                    nib.Nifti1Image(
                        warped_roi.astype(np.float32),
                        dwi_affine), fname)
                meta = dict()
                meta_fname = fname.split('.')[0] + '.json'
                afd.write_json(meta_fname, meta)
            roi_files[bundle].append(fname)
    return {'rois_file': roi_files}


@pimms.calc("mapping")
def mapping(subses_dict, reg_subject, data_imap, bids_info,
            mapping_definition=None):
    """
    mapping from subject to template space.

    Parameters
    ----------
    mapping_definition : instance of `AFQ.definitions.mapping`, optional
        This defines how to either create a mapping from
        each subject space to template space or load a mapping from
        another software. If creating a map, will register reg_subject and
        reg_template.
        If None, use SynMap()
        Default: None
    """
    reg_template = data_imap["reg_template"]
    if mapping_definition is None:
        mapping_definition = SynMap()
    if not isinstance(mapping_definition, Definition):
        raise TypeError(
            "mapping must be a mapping defined"
            + " in `AFQ.definitions.mapping`")
    if bids_info is not None:
        mapping_definition.find_path(
            bids_info["bids_layout"],
            subses_dict["dwi_file"],
            bids_info["subject"],
            bids_info["session"])
    return mapping_definition.get_for_subses(
        subses_dict, bids_info, reg_subject, reg_template)


@pimms.calc("mapping")
def sls_mapping(subses_dict, reg_subject, data_imap, bids_info,
                tractography_imap, mapping_definition=None):
    """
    mapping from subject to template space.

    Parameters
    ----------
    mapping_definition : instance of `AFQ.definitions.mapping`, optional
        This defines how to either create a mapping from
        each subject space to template space or load a mapping from
        another software. If creating a map, will register reg_subject and
        reg_template.
        If None, use SynMap()
        Default: None
    """
    reg_template = data_imap["reg_template"]
    if mapping_definition is None:
        mapping_definition = SynMap()
    if not isinstance(mapping_definition, Definition):
        raise TypeError(
            "mapping must be a mapping defined"
            + " in `AFQ.definitions.mapping`")
    if bids_info is not None:
        mapping_definition.find_path(
            bids_info["bids_layout"],
            subses_dict["dwi_file"],
            bids_info["subject"],
            bids_info["session"])
    streamlines_file = tractography_imap["streamlines_file"]
    tg = load_tractogram(
        streamlines_file, reg_subject,
        Space.VOX, bbox_valid_check=False)
    tg.to_rasmm()

    atlas_fname = op.join(
        afd.afq_home,
        'hcp_atlas_16_bundles',
        'Atlas_in_MNI_Space_16_bundles',
        'whole_brain',
        'whole_brain_MNI.trk')
    if not op.exists(atlas_fname):
        afd.fetch_hcp_atlas_16_bundles()
    hcp_atlas = load_tractogram(
        atlas_fname,
        'same', bbox_valid_check=False)
    return mapping_definition.get_for_subses(
        subses_dict, bids_info, reg_subject, reg_template,
        subject_sls=tg.streamlines,
        template_sls=hcp_atlas.streamlines)


@pimms.calc("reg_subject")
def get_reg_subject(data_imap, bids_info, subses_dict, dwi_affine,
                    reg_subject_spec="power_map"):
    """
    Nifti1Image which represents this subject
    when registering the subject to the template

    Parameters
    ----------
    reg_subject_spec : str, instance of `AFQ.definitions.scalar`, optional  # noqa
        The source image data to be registered.
        Can either be a Nifti1Image, a scalar definition, or str.
        if "b0", "dti_fa_subject", "subject_sls", or "power_map,"
        image data will be loaded automatically.
        If "subject_sls" is used, slr registration will be used
        and reg_template should be "hcp_atlas".
        Default: "power_map"
    """
    reg_template = data_imap["reg_template"]
    if not isinstance(reg_subject_spec, str)\
            and not isinstance(reg_subject_spec, nib.Nifti1Image)\
            and not isinstance(reg_subject_spec, Definition):
        raise TypeError(
            "reg_subject must be a str, Definition, or Nifti1Image")

    filename_dict = {
        "b0": data_imap["b0_file"],
        "power_map": data_imap["pmap_file"],
        "dti_fa_subject": data_imap["dti_fa_file"],
        "subject_sls": data_imap["b0_file"],
    }
    bm = nib.load(data_imap["brain_mask_file"])

    if bids_info is not None and isinstance(reg_subject_spec, Definition):
        reg_subject_spec.find_path(
            bids_info["bids_layout"],
            subses_dict["dwi_file"],
            bids_info["subject"],
            bids_info["session"])
        reg_subject_spec = reg_subject_spec.get_data(
            subses_dict, bids_info, dwi_affine,
            reg_template, None)
    else:
        if reg_subject_spec in filename_dict:
            reg_subject_spec = filename_dict[reg_subject_spec]
    img = nib.load(reg_subject_spec)
    bm = bm.get_fdata().astype(bool)
    masked_data = img.get_fdata()
    masked_data[~bm] = 0
    img = nib.Nifti1Image(masked_data, img.affine)
    return img


def get_mapping_plan(kwargs, use_sls=False):
    mapping_tasks = with_name([
        export_registered_b0, template_xform, export_rois, mapping,
        get_reg_subject])

    bids_info = kwargs.get("bids_info", None)
    # add custom scalars
    for scalar in kwargs["scalars"]:
        if isinstance(scalar, Definition):
            if bids_info is None:
                scalar.find_path(
                    None,
                    kwargs["subses_dict"]["dwi_file"],
                    None,
                    None
                )
            else:
                scalar.find_path(
                    bids_info["bids_layout"],
                    kwargs["subses_dict"]["dwi_file"],
                    bids_info["subject"],
                    bids_info["session"]
                )
            mapping_tasks["{scalar.name}_file_res"] =\
                pimms.calc(f"{scalar.name}_file")(scalar.get_for_subses())

    if use_sls:
        mapping_tasks["mapping_res"] = sls_mapping

    return pimms.plan(**mapping_tasks)
