
import polars as pl
from anypytools import AnyPyProcess
import anypytools.macro_commands as mc
import numpy as np


# Maps the DOF name to its description/axis-label and sign convention compared to AMS
dof_map = {
    "HipFlexion": ("Hip extension(-)/flexion(+)", 1),
    "HipAbduction": ("Hip abduction(-)/adduction(+)", -1),
    "HipExternalRotation": ("Hip external(-)/internal(+) rotation", -1),
    "KneeFlexion": ("Knee extension(-)/flexion(+)", 1),
    "AnklePlantarFlexion": ("Ankle plantar(-)/dorsi(+)flexion", -1),
    "SubtalarEversion": ("Ankle eversion(-)/inversion(+)", -1),
}

# Maps the AnyBody strength study name to the columns in the output
study_map = {
    "HipFlexion": "Hip flexion",
    "HipExtension": "Hip extension",
    "HipAbduction": "Hip abduction",
    "HipAdduction": "Hip adduction",
    "HipExternalRotation": "Hip external rotation",
    "HipInternalRotation": "Hip internal rotation",
    "KneeFlexion": "Knee flexion",
    "KneeExtension": "Knee extension",
    "AnklePlantarFlexion": "Ankle plantarflexion",
    "AnkleDorsiFlexion": "Ankle dorsiflexion",
    "SubTalarEversion": "Ankle eversion",
    "SubTalarInversion": "Ankle inversion",
}

# This plan for the batch simulation defines for each study (key) which is the primary and secondary DOF (value)
simulation_plan: dict[str, tuple[str, str]] = {
    "AnkleDorsiFlexion": ("AnklePlantarFlexion", "KneeFlexion"),
    "AnklePlantarFlexion": ("AnklePlantarFlexion", "KneeFlexion"),
    "SubTalarEversion": ("SubtalarEversion", "AnklePlantarFlexion"),
    "SubTalarInversion": ("SubtalarEversion", "AnklePlantarFlexion"),
    "HipAbduction": ("HipAbduction", "HipFlexion"),
    "HipAdduction": ("HipAbduction", "HipFlexion"),
    "HipExtension": ("HipFlexion", "KneeFlexion"),
    "HipFlexion": ("HipFlexion", "KneeFlexion"),
    "HipExternalRotation": ("HipExternalRotation", "HipFlexion"),
    "HipInternalRotation": ("HipExternalRotation", "HipFlexion"),
    "KneeExtension": ("KneeFlexion", "HipFlexion"),
    "KneeFlexion": ("KneeFlexion", "HipFlexion"),

}

# Define the range of motion for each study
range_of_motion = {
"AnkleDorsiFlexion": np.array([30, -30]),
"AnklePlantarFlexion": np.array([-30, 30]),
"KneeFlexion": np.array([0, 160]),
"KneeExtension": np.array([160, 0]),
"SubTalarEversion": np.array([-20.0, 20.0]),
"SubTalarInversion": np.array([-20.0, 20.0]),
"HipAbduction": np.array([-15, 40]),
"HipAdduction": np.array([40, -15]),
"HipExtension": np.array([130, -5]),
"HipFlexion": np.array([-5, 130]),
"HipExternalRotation": np.array([-20.0, 20.0]),
"HipInternalRotation": np.array([-20.0, 20.0]),
}

# Define the range of motion for each study
rom_secondary_dof = {
"AnklePlantarFlexion": np.array([-30, 30]),
"KneeFlexion": np.array([0, 160]),
"HipFlexion": np.array([-5, 130]),
}

macros = []

for study, (primary_dof, secondary_dof) in simulation_plan.items():
    rom_primary = range_of_motion[study]
    submacros = []
    rom_secondary = np.linspace(*rom_secondary_dof[secondary_dof], 40)
    for secondary_val in rom_secondary:
        submacros.append([
            mc.Load("EvaluateJointStrength.main.any"),
            # Set parameters for easier output

            mc.SetValue(f"Main.HumanModel.EvaluateJointStrength.Right.Leg.{study}.RangeOfMotion", rom_primary ),
            mc.SetValue(f"Main.HumanModel.EvaluateJointStrength.Right.Leg.{study}.{secondary_dof}", secondary_val),
            mc.OperationRun(f"Main.HumanModel.EvaluateJointStrength.Right.Leg.{study}.Study.InverseDynamics"),

            mc.Export(f"Main.HumanModel.EvaluateJointStrength.Right.Leg.{study}.Study.Output.JointStrength.Abscissa.JointAngle", "measurePrimaryDoF"),
            mc.Export(f"Main.HumanModel.EvaluateJointStrength.Right.Leg.{study}.Study.Output.JointStrength.JointStrength", "measureValue"),
            mc.ExtendOutput("measureObject", study_map[study]),
            mc.ExtendOutput("primaryDoF", dof_map[primary_dof][0]),
            mc.ExtendOutput("secondaryDoF", dof_map[secondary_dof][0]),
            mc.ExtendOutput("measureSecondDoF", secondary_val),
            mc.ExtendOutput("measureSecondDoFSign", dof_map[secondary_dof][1]),
            mc.ExtendOutput("measurePrimaryDoFSign", dof_map[primary_dof][1]),
        ])
    macros.extend(submacros)

app = AnyPyProcess(num_processes=5)
results = app.start_macro(macros)

df_pandas = results.to_dataframe(index_var="measurePrimaryDoF")

# Change signs of variables which are opposite to the AnyBody convention
df = pl.from_pandas(df_pandas).with_columns(
    pl.col("measureSecondDoF")*pl.col("measureSecondDoFSign").alias("measureSecondDoF"),
    pl.col("measurePrimaryDoF")*pl.col("measurePrimaryDoFSign").alias("measurePrimaryDoF"),
).drop(["measureSecondDoFSign", "measurePrimaryDoFSign"])

df.write_parquet("joint_strength_results.parquet")

print(df)