"""
Blender Script

Automated Dick Rigging and Weight Painting
Version 0.08

Author: notcreative
"""



# Flag to determine if the user has correctly positioned the reference empties.
# Initially False, set to True after the user manually positions the reference empties.
FOUND_CORRECT_POSITION = False

# The MEMBER_MESH is for the dick mesh but can also be the character mesh if the dick is already fused
MEMBER_MESH = "Genesis 9 Mesh"
# This is the bone that the "shaft" will connect to, typically the pelvis or hip
MEMBER_ROOT_BONE = "pelvis"
# The ARMATURE_ROOT_BONE is the first bone in the hierarchy, excluding the armature itself
ARMATURE_ROOT_BONE = "master"
# The CHARACTER_RIG is the armature of the character
CHARACTER_RIG = "Genesis 9"



# _________________________________________________________________________________________________________________________________________
# Rigging:

# Constants for names
MEMBER_NAME = "Iron"  # IMPORTANT: Avoid naming the MEMBER_NAME the same as existing bone names (e.g., 'shaft').
#                       Such names may cause conflicts because the script requires unique names for the dick.
COLLECTION_NAME = "Iron Collection"


# Number of bones
NUMBER_BONES = 10
NUMBER_HEAD_BONES = 0


# List of specific bones to be moved to COLLECTION_NAME for better organization.
# If you get this error: "AttributeError: 'Armature' object has no attribute 'collections_all'. Did you mean: 'collections'?"
MOVE_CUSTOM_BONES_TO_COLLECTION = True  # Set this to False
CUSTOM_BONES_TO_MOVE_TO_COLLECTION = ["l_testicle", "r_testicle", "scrotum"]


# List of items (bone names and vertex groups) to be removed during the cleanup phase of the rigging process.
# Any item that contains the string "shaft" in their name will be removed. ("shaft_1", "shaft_2", "shaft_3", etc...).
ORIGINAL_ITEMS_TO_REMOVE = ["foreskin", "glans", "urethra", "shaft"]
DELETE_ORIGINAL_MEMBER_BONES = False
DELETE_ORIGINAL_MEMBER_VERTEX_GROUPS = True


# Twist controller
TWIST_CONTROLLER_MIM = -25
TWIST_CONTROLLER_MAX = 25
TWIST_CONTROLLER_CUSTOM_INFLUENCES = {
    f'{MEMBER_NAME}': 0.0,
    f'{MEMBER_NAME}.001': 0.25,
    f'{MEMBER_NAME}.002': 0.5,
}



# _________________________________________________________________________________________________________________________________________
# Weight Painting

# These envelope settings determine the initial influence radius of the bones on the mesh.
# Adjust these values if the deformation is too strong or too weak.
ENVELOPE_START_DISTANCE = 0.035

# Adjust the envelope distances below to fine-tune the rigging influence of specific bones.
# These settings reduce the default impact on the body mesh.
CUSTOM_ENVELOPE_DISTANCES = {
    f'{MEMBER_NAME}': 0.01,
    f'{MEMBER_NAME}.001': 0.02,
    f'{MEMBER_NAME}.002': 0.02,
    f'{MEMBER_NAME}.003': 0.03
}

VERTEX_GROUP_LEVELS_OFFSET = 0.0  # For smaller dicks use: -0.95
VERTEX_GROUP_LEVELS_GAIN = 1.0    # For smaller dicks use: 50

VERTEX_GROUP_SMOOTH_FACTOR = 0.5
VERTEX_GROUP_SMOOTH_REPEAT = 100
VERTEX_GROUP_SMOOTH_EXPAND = 0.0



# _________________________________________________________________________________________________________________________________________
# Gizmos settings
CONTROLLER_SIZE_MULTIPLIER = 1.5





# _________________________________________________________________________________________________________________________________________
# DO NOT TOUCH BELOW
# _________________________________________________________________________________________________________________________________________

# TODO - Create an option to use the already created weight paints

import bpy
import math
from mathutils import Vector

SPLINE_IK_CHAIN_COUNT = NUMBER_BONES - NUMBER_HEAD_BONES
SPLINE_IK_START_BONE = None
LAST_MEMBER_BONE = None


# Utility Functions

def clean_previous_data():
    """ Cleans up the scene by removing specified bones and objects. """
    set_active_object(CHARACTER_RIG, mode='EDIT')

    for bone in bpy.context.object.data.edit_bones:
        if MEMBER_NAME.lower() in bone.name.lower():
            bpy.context.object.data.edit_bones.remove(bone)

    set_active_object(CHARACTER_RIG, mode='OBJECT')

    for obj in bpy.context.scene.objects:
        if obj.name.startswith(MEMBER_NAME) and obj.type in ['CURVE', 'EMPTY']:
            # Names of objects to keep
            keep_names = [
                f'{MEMBER_NAME} Base_Position',
                f'{MEMBER_NAME} Tip_Position',
                f'{MEMBER_NAME} Position Bezier_Curve'
            ]
            # If object's name is not in the list of names to keep, remove it
            if all(obj.name != keep_name for keep_name in keep_names):
                bpy.data.objects.remove(obj, do_unlink=True)

    for coll in bpy.data.collections:
        if MEMBER_NAME.lower() in coll.name.lower():
            bpy.data.collections.remove(coll)

    set_active_object(MEMBER_MESH, mode='OBJECT')

    for group in bpy.context.object.vertex_groups:
        if MEMBER_NAME.lower() in group.name.lower():
            bpy.context.object.vertex_groups.remove(group)

def set_active_object(obj_name, mode='OBJECT'):
    bpy.ops.object.mode_set(mode='OBJECT')  # Safely switch to object mode first to avoid context errors

    obj = bpy.data.objects.get(obj_name)
    if not obj:
        raise ValueError(f"Object named '{obj_name}' not found.")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode=mode)

def deselect_all_bones():
    bpy.ops.object.mode_set(mode='EDIT')  # Ensure we are in edit mode
    for bone in bpy.context.object.data.edit_bones:
        bone.select = False
def select_and_activate_bone(bone_name):
    mode = bpy.context.object.mode  # Capture the current mode of the object
    deselect_all_bones()

    if mode == 'EDIT':
        bone = bpy.context.object.data.edit_bones.get(bone_name)
    elif mode == 'POSE':
        bone = bpy.context.object.pose.bones.get(bone_name)
    else:
        raise ValueError("This function only works in Edit Mode or Pose Mode.")

    if bone:
        if mode == 'EDIT':
            bone.select = True
            bpy.context.object.data.edit_bones.active = bone
        elif mode == 'POSE':
            bone.bone.select = True
            bpy.context.object.data.bones.active = bone.bone
    else:
        raise ValueError(f"Bone named '{bone_name}' not found.")
def select_bones_by_name_contains(armature, substring, exclude_substrings=None):
    # Save the current mode
    current_mode = bpy.context.object.mode

    # Select rig
    bpy.data.objects[armature].select_set(True)
    bpy.context.view_layer.objects.active = bpy.data.objects[armature]

    bpy.ops.object.mode_set(mode='POSE')

    # Initialize flag to track if any bone was selected
    any_bone_selected = False

    # Deselect all pose bones first to ensure a clean selection
    for bone in bpy.context.object.pose.bones:
        if substring in bone.name and not any(substring in bone.name for substring in (exclude_substrings or [])):
            bone.bone.select = True
            if not any_bone_selected:
                bpy.context.object.data.bones.active = bone.bone
                any_bone_selected = True
        else:
            bone.bone.select = False

    if not any_bone_selected:
        raise ValueError(f"No suitable bones containing '{substring}' found in the armature.")

    # Restore previous mode
    bpy.ops.object.mode_set(mode=current_mode)
def assign_bones_to_collection(armature, bone_names, collection_name, remove_from_others=False):
    # Only run this function if the current Blender version is Blender 4.0 or higher
    if bpy.app.version[0] >= 4 and MOVE_CUSTOM_BONES_TO_COLLECTION:

        # Save the current mode
        current_mode = bpy.context.object.mode

        bpy.ops.object.mode_set(mode='EDIT')

        # Convert bone_names to a list if it is not already one
        if isinstance(bone_names, str):
            bone_names = [bone_names]

        if remove_from_others:
            # Remove bones from all their current collections
            for bone_name in bone_names:
                if bone_name in armature.data.edit_bones:
                    for collection in armature.data.edit_bones[bone_name].collections:
                        collection.unassign(armature.data.edit_bones[bone_name])

        # Check if the target collection already exists and assign the bone
        collection_found = False
        for collection in armature.data.collections_all:
            if collection.name == collection_name:
                for bone_name in bone_names:
                    if bone_name in armature.data.edit_bones:
                        collection.assign(armature.data.edit_bones[bone_name])
                collection_found = True
                break

        # If the collection was not found, create it and assign the bones
        if not collection_found:
            new_collection = armature.data.collections.new(collection_name)
            for bone_name in bone_names:
                if bone_name in armature.data.edit_bones:
                    new_collection.assign(armature.data.edit_bones[bone_name])

        # Finalize
        bpy.ops.object.mode_set(mode=current_mode)
def setup_control_bone(control, parent_bone, head_position, tail_position):
    bone_name = f"{MEMBER_NAME} {control}"
    bpy.ops.armature.bone_primitive_add(name=bone_name)
    control_bone = bpy.context.object.data.edit_bones[bone_name]
    control_bone.parent = bpy.context.object.data.edit_bones[parent_bone]
    control_bone.head = head_position
    control_bone.tail = tail_position

    assign_bones_to_collection(bpy.context.object, bone_name, COLLECTION_NAME, remove_from_others=True)
def find_bone_at_depth(bone, depth):
    if depth == 0:
        return bone
    if not bone.children:
        return None  # If no children and depth not zero, we can't go deeper
    for child_bone in bone.children:
        result = find_bone_at_depth(child_bone, depth - 1)
        if result is not None:  # Only return if we actually find something
            return result

def get_collection(ob):
    for coll in bpy.data.collections:
        if ob.name in coll.objects.keys():
            return coll
    return bpy.context.scene.collection
def create_collection_and_link_to_it(obj, collection_name, remove_from_others=False, link_to_collection=None):
    scene_collection = bpy.context.scene.collection

    # Remove the object from the scene collection so it can move to the new collection
    if obj.name in scene_collection.objects:
        scene_collection.objects.unlink(obj)

    if remove_from_others:
        # Remove the object from all other collections
        current_collections = [col for col in bpy.data.collections if obj.name in [o.name for o in col.objects]]
        for col in current_collections:
            col.objects.unlink(obj)

    # Check if the collection already exists, if not, create it
    collection = bpy.data.collections.get(collection_name)
    if not collection:
        collection = bpy.data.collections.new(collection_name)
        if link_to_collection:
            link_to_collection.children.link(collection)
        else:
            scene_collection.children.link(collection)  # Link the new collection to the scene collection

    # Link the object to the collection if it's not already linked
    if obj.name not in [o.name for o in collection.objects]:
        collection.objects.link(obj)

    return collection

def set_bezier_control_point_positions(bezier_curve, control_target, index):
    """
    Sets the position of a Bezier curve control point based on either a bone or an object and assigns a hook modifier.

    """
    # Determine the target and setup hook modifier parameters
    if isinstance(control_target, tuple):
        armature, bone_name = control_target
        control_point = armature.pose.bones.get(bone_name).head
        hook_target = armature
        hook_subtarget = bone_name
    else:
        control_point = control_target.location
        hook_target = control_target
        hook_subtarget = ""

    # Activate the Bezier curve and set the control point
    set_active_object(bezier_curve.name, mode='EDIT')

    bpy.ops.curve.select_all(action='DESELECT')
    point = bezier_curve.data.splines[0].bezier_points[index]
    point.select_control_point = True
    point.select_left_handle = True
    point.select_right_handle = True
    point.co = control_point

    # Assign a hook modifier to the control point
    hook_modifier = bezier_curve.modifiers.new(name=f'Hook {index}', type='HOOK')
    hook_modifier.object = hook_target
    if hook_subtarget:
        hook_modifier.subtarget = hook_subtarget
    bpy.ops.object.hook_assign(modifier=hook_modifier.name)

def create_display_empty(name, collection=None, display_type='CIRCLE', display_size=1.0, location=(0, 0, 0), hide_render=True, hide_select=True, hide_viewport=True, show_in_front=False):
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.empty_add(type=display_type, location=location)
    empty = bpy.context.object
    empty.name = name

    # Link to the specified collection if provided
    if collection:
        create_collection_and_link_to_it(empty, collection, True, get_collection(bpy.data.objects.get(CHARACTER_RIG)))

    # Configure visibility settings
    empty.empty_display_type = display_type
    empty.empty_display_size = display_size
    empty.hide_render = hide_render
    empty.hide_select = hide_select
    empty.hide_viewport = hide_viewport
    empty.show_in_front = show_in_front

    return empty


# Main Functionalities


def setup_bone_position():
    """
    Sets up visual markers for base and tip positions of a bone and creates a corresponding Bezier curve.
    """
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

    empty_base = create_display_empty(f'{MEMBER_NAME} Base_Position', collection=None, display_type='PLAIN_AXES', display_size=0.05,
                                      location=(0, 0, 0.7), hide_render=True, hide_select=False, hide_viewport=False, show_in_front=True)
    empty_tip = create_display_empty(f'{MEMBER_NAME} Tip_Position', collection=None, display_type='PLAIN_AXES', display_size=0.05,
                                     location=(0, -0.4, 0.7), hide_render=True, hide_select=False, hide_viewport=False, show_in_front=True)

    bpy.ops.curve.primitive_bezier_curve_add()
    bezier_curve = bpy.context.object
    bezier_curve.name = f'{MEMBER_NAME} Position Bezier_Curve'
    bezier_curve.show_in_front = True

    set_bezier_control_point_positions(bezier_curve, empty_base, 0)
    set_bezier_control_point_positions(bezier_curve, empty_tip, 1)

    bpy.ops.curve.select_all(action='SELECT')
    bpy.ops.curve.handle_type_set(type='AUTOMATIC')

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    bpy.data.objects[f'{MEMBER_NAME} Base_Position'].select_set(True)
    bpy.data.objects[f'{MEMBER_NAME} Tip_Position'].select_set(True)
def get_setup_bone_position():
    """
    Retrieves the positions of the base and tip markers for a bone setup.
    """
    base = bpy.data.objects.get(f'{MEMBER_NAME} Base_Position')
    if not base:
        raise ValueError(f'Couldn\'t find "{MEMBER_NAME} Base_Position".')

    tip = bpy.data.objects.get(f'{MEMBER_NAME} Tip_Position')
    if not tip:
        raise ValueError(f'Couldn\'t find "{MEMBER_NAME} Tip_Position".')

    return base.location, tip.location
def clear_setup_bone_position():
    """
    Clears all objects created for setting up bone positions.
    """
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

    bpy.data.objects[f'{MEMBER_NAME} Base_Position'].select_set(True)
    bpy.data.objects[f'{MEMBER_NAME} Tip_Position'].select_set(True)
    bpy.data.objects[f'{MEMBER_NAME} Position Bezier_Curve'].select_set(True)

    bpy.ops.object.delete()

def setup_new_member_bone():
    """ Creates a new member bone with specified configurations. """
    set_active_object(CHARACTER_RIG, mode='EDIT')
    bpy.ops.armature.bone_primitive_add(name=MEMBER_NAME)
    select_and_activate_bone(MEMBER_NAME)

    armature = bpy.context.object

    # Only run this function if the current Blender version is Blender 4.0 or higher
    assign_bones_to_collection(armature, MEMBER_NAME, COLLECTION_NAME, remove_from_others=True)
    assign_bones_to_collection(armature, CUSTOM_BONES_TO_MOVE_TO_COLLECTION, COLLECTION_NAME, remove_from_others=True)

    member_base, member_tip = get_setup_bone_position()

    member_bone = armature.data.edit_bones[MEMBER_NAME]
    member_bone.head = member_base
    member_bone.tail = member_tip
    member_bone.parent = armature.data.edit_bones[MEMBER_ROOT_BONE]
    member_bone.inherit_scale = 'NONE'
    member_bone.envelope_distance = ENVELOPE_START_DISTANCE
    member_bone.head_radius = 0.013
    member_bone.tail_radius = 0.013

    bpy.ops.armature.subdivide(number_cuts=NUMBER_BONES - 1)

    # Reorganize bones
    armature.data.edit_bones[MEMBER_NAME].name = f'{MEMBER_NAME}_TEMP_MAIN'

    # Function to recursively rename and number bones
    def rename_bone(bone, new_sub_name):
        for child_bone in bone.children:
            armature.data.edit_bones[child_bone.name].name = f'{MEMBER_NAME}{new_sub_name}'
            rename_bone(child_bone, new_sub_name)

    rename_bone(armature.data.edit_bones[f'{MEMBER_NAME}_TEMP_MAIN'], '_TEMP')
    armature.data.edit_bones[f'{MEMBER_NAME}_TEMP_MAIN'].name = MEMBER_NAME
    rename_bone(armature.data.edit_bones[MEMBER_NAME], '')

    for bone in armature.data.edit_bones:
        if bone.name in CUSTOM_ENVELOPE_DISTANCES:
            bone.envelope_distance = CUSTOM_ENVELOPE_DISTANCES[bone.name]

def create_weight_blends():
    """
    Applies weight blends to the member mesh object to influence how the mesh
    deforms in relation to the bones.
    """
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

    set_active_object(CHARACTER_RIG, mode='EDIT')
    select_bones_by_name_contains(CHARACTER_RIG, MEMBER_NAME, exclude_substrings=["Control"])

    bpy.data.objects[CHARACTER_RIG].select_set(True)
    bpy.data.objects[MEMBER_MESH].select_set(True)
    bpy.context.view_layer.objects.active = bpy.data.objects[MEMBER_MESH]

    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')

    bpy.ops.paint.weight_from_bones(type='ENVELOPES')
    bpy.ops.object.vertex_group_levels(group_select_mode='BONE_SELECT', offset=VERTEX_GROUP_LEVELS_OFFSET, gain=VERTEX_GROUP_LEVELS_GAIN)
    bpy.ops.object.vertex_group_smooth(group_select_mode='BONE_SELECT', factor=VERTEX_GROUP_SMOOTH_FACTOR, repeat=VERTEX_GROUP_SMOOTH_REPEAT, expand=VERTEX_GROUP_SMOOTH_EXPAND)

def create_control_bones():
    """
    Generates control bones that serve as manipulators for the rig, allowing
    animators to control the rig more intuitively.
    """
    global SPLINE_IK_START_BONE
    global LAST_MEMBER_BONE

    # Create display empty and ensure control bones collection exists
    create_display_empty(f'{MEMBER_NAME} Controls_Display', f"{MEMBER_NAME} Controls")

    # Ensure the character rig is selected and set to edit mode
    bpy.data.objects[CHARACTER_RIG].select_set(True)
    bpy.context.view_layer.objects.active = bpy.data.objects[CHARACTER_RIG]

    set_active_object(CHARACTER_RIG, mode='EDIT')

    SPLINE_IK_START_BONE = find_bone_at_depth(bpy.context.object.data.bones[MEMBER_NAME], SPLINE_IK_CHAIN_COUNT - 1).name
    LAST_MEMBER_BONE = find_bone_at_depth(bpy.context.object.data.bones[MEMBER_NAME], NUMBER_BONES - 1).name

    # Define control bones and settings
    setup_control_bone('Control_1', MEMBER_ROOT_BONE, bpy.context.object.data.bones[MEMBER_NAME].head_local, bpy.context.object.data.bones[MEMBER_NAME].tail_local)
    setup_control_bone('Control_2', ARMATURE_ROOT_BONE, bpy.context.object.data.bones[SPLINE_IK_START_BONE].tail_local,
                       bpy.context.object.data.bones[SPLINE_IK_START_BONE].tail_local - Vector((0.0, bpy.context.object.data.bones[LAST_MEMBER_BONE].length, 0.0)))
    setup_control_bone('Control_3', ARMATURE_ROOT_BONE, bpy.context.object.data.bones[LAST_MEMBER_BONE].tail_local - Vector(
        (0.0, 0.1, 0.0)), bpy.context.object.data.bones[LAST_MEMBER_BONE].tail_local - Vector((0.0, bpy.context.object.data.bones[LAST_MEMBER_BONE].length, 0.0)) - Vector((0.0, 0.1, 0.0)))

    # Switch to pose mode for setting custom shapes
    bpy.ops.object.mode_set(mode='POSE')
    for each_bone in bpy.context.active_object.pose.bones:
        if f'{MEMBER_NAME} Control' in each_bone.name:
            each_bone.custom_shape = bpy.data.objects[f'{MEMBER_NAME} Controls_Display']
            each_bone.custom_shape_scale_xyz = Vector((CONTROLLER_SIZE_MULTIPLIER, CONTROLLER_SIZE_MULTIPLIER, CONTROLLER_SIZE_MULTIPLIER))

def create_member_bezier_curve():
    """
    Creates a Bezier curve, places it within a specific collection, and sets up hook modifiers linked to control bones.
    """
    bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.curve.primitive_bezier_curve_add()
    bezier_curve = bpy.context.object
    bezier_curve.name = f'{MEMBER_NAME} Bezier_Curve'

    create_collection_and_link_to_it(bezier_curve, f'{MEMBER_NAME} Controls', get_collection(bpy.data.objects.get(CHARACTER_RIG)))

    bpy.ops.object.mode_set(mode='EDIT')

    set_bezier_control_point_positions(bezier_curve, (bpy.data.objects[CHARACTER_RIG], f'{MEMBER_NAME} Control_1'), 0)
    set_bezier_control_point_positions(bezier_curve, (bpy.data.objects[CHARACTER_RIG], f'{MEMBER_NAME} Control_2'), 1)

    # Extrude the curve (for some reason I need to extrude it HERE or it fucks up)
    bpy.ops.curve.extrude_move()

    set_bezier_control_point_positions(bezier_curve, (bpy.data.objects[CHARACTER_RIG], f'{MEMBER_NAME} Control_3'), 2)

    bpy.ops.curve.select_all(action='SELECT')
    bpy.ops.curve.handle_type_set(type='AUTOMATIC')
    bpy.ops.curve.handle_type_set(type='ALIGNED')
def set_follow_spline():
    """
    Configures the spline IK constraint.
    """
    set_active_object(CHARACTER_RIG, mode='EDIT')

    bpy.ops.object.mode_set(mode='POSE')

    select_and_activate_bone(SPLINE_IK_START_BONE)

    spline_ik_constraint = bpy.data.objects[CHARACTER_RIG].pose.bones[SPLINE_IK_START_BONE].constraints.new(type='SPLINE_IK')
    spline_ik_constraint.name = f'Spline_IK {MEMBER_NAME} Constraint'

    spline_ik_constraint.target = bpy.data.objects[f'{MEMBER_NAME} Bezier_Curve']
    spline_ik_constraint.chain_count = SPLINE_IK_CHAIN_COUNT
    spline_ik_constraint.y_scale_mode = "BONE_ORIGINAL"

def create_twist_controller():
    """
    Creates a twist controller bone for the dicks's rotation around the Y-axis. It also applies constraints to limit the rotation.
    """
    set_active_object(CHARACTER_RIG, mode='EDIT')

    bone_name = f'{MEMBER_NAME} Twist_Control'
    bpy.ops.armature.bone_primitive_add(name=bone_name)
    twist_bone = bpy.context.object.data.edit_bones[bone_name]
    twist_bone.head = bpy.context.object.data.bones[MEMBER_NAME].head_local
    twist_bone.tail = bpy.context.object.data.bones[MEMBER_NAME].tail_local
    twist_bone.parent = bpy.context.object.data.edit_bones[MEMBER_ROOT_BONE]

    assign_bones_to_collection(bpy.context.object, bone_name, COLLECTION_NAME, remove_from_others=True)

    bpy.ops.object.mode_set(mode='POSE')

    pose_bone = bpy.context.object.pose.bones[bone_name]
    pose_bone.custom_shape = bpy.data.objects.get(f"{MEMBER_NAME} Controls_Display")
    pose_bone.custom_shape_scale_xyz = Vector((2.5, 2.5, 2.5))

    # Limit transform
    pose_bone.lock_location[0] = pose_bone.lock_location[1] = pose_bone.lock_location[2] = True
    pose_bone.lock_rotation[0] = pose_bone.lock_rotation[2] = True  # Lock X, Lock Z

    # Limit rotation constraint
    limit_rot = pose_bone.constraints.new(type='LIMIT_ROTATION')
    limit_rot.name = f'Limit_Rotation {MEMBER_NAME} Constraint'
    limit_rot.owner_space = 'LOCAL'
    limit_rot.use_limit_x = limit_rot.use_limit_y = limit_rot.use_limit_z = True

    limit_rot.min_y = math.radians(TWIST_CONTROLLER_MIM)
    limit_rot.max_y = math.radians(TWIST_CONTROLLER_MAX)

    # Add rotation constraints to rest of member
    for bone in bpy.context.object.pose.bones:
        if f'{MEMBER_NAME}' in bone.name and 'Control' not in bone.name:
            copy_rot = bone.constraints.new(type='COPY_ROTATION')
            copy_rot.name = bone_name
            copy_rot.target = bpy.data.objects[CHARACTER_RIG]
            copy_rot.subtarget = bone_name
            copy_rot.mix_mode = 'ADD'
            copy_rot.target_space = 'LOCAL'
            copy_rot.owner_space = 'LOCAL'
            if bone.name in TWIST_CONTROLLER_CUSTOM_INFLUENCES:
                copy_rot.influence = TWIST_CONTROLLER_CUSTOM_INFLUENCES[bone.name]

def remove_original_member_bones():
    set_active_object(CHARACTER_RIG, mode='EDIT')

    # Collect bones that match the items to be removed and delete them
    bones_to_remove = [bone for bone in bpy.context.object.data.edit_bones if any(item.lower() in bone.name.lower() for item in ORIGINAL_ITEMS_TO_REMOVE)]
    for bone in bones_to_remove:
        bpy.context.object.data.edit_bones.remove(bone)

    # Force an update
    # bpy.context.object.data.update()
def remove_original_member_vertex_groups():
    # Ensure the member mesh is active and set to object mode for vertex group manipulation
    set_active_object(MEMBER_MESH, mode='OBJECT')

    # Collect vertex groups that match the items to be removed and delete them
    groups_to_remove = [group for group in bpy.context.object.vertex_groups if any(item.lower() in group.name.lower() for item in ORIGINAL_ITEMS_TO_REMOVE)]
    for group in groups_to_remove:
        bpy.context.object.vertex_groups.remove(group)

    # Force an update
    bpy.context.object.data.update()


def initialize():
    bpy.context.scene.cursor.location = (0, 0, 0)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.data.objects[CHARACTER_RIG].select_set(True)
    bpy.context.view_layer.objects.active = bpy.data.objects[CHARACTER_RIG]
def main():
    if bpy.context.object.type != 'ARMATURE':
        print("The selected object is not an armature. Please select an armature and rerun the script.")
        return

    clean_previous_data()

    if not FOUND_CORRECT_POSITION:
        setup_bone_position()
    else:
        setup_new_member_bone()
        create_weight_blends()
        create_control_bones()
        create_member_bezier_curve()
        set_follow_spline()
        create_twist_controller()

        if DELETE_ORIGINAL_MEMBER_BONES:
            remove_original_member_bones()
        if DELETE_ORIGINAL_MEMBER_VERTEX_GROUPS:
            remove_original_member_vertex_groups()

        clear_setup_bone_position()


if __name__ == "__main__":
    initialize()
    main()
