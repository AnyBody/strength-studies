
import polars as pl
from anypytools import AnyPyProcess
import anypytools.macro_commands as mc
import numpy as np

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



range_of_motion = {
"AnkleDorsiFlexion": np.array([-20.0, 20.0]),
"AnklePlantarFlexion": np.array([-20.0, 20.0]),
"KneeFlexion": np.array([0, 160]),
"KneeExtension": np.array([160, 0]),
"SubTalarEversion": np.array([-20.0, 20.0]),
"SubTalarInversion": np.array([-20.0, 20.0]),
"HipAbduction": np.array([-20.0, 20.0]),
"HipAdduction": np.array([-20.0, 20.0]),
"HipExtension": np.array([-20.0, 20.0]),
"HipFlexion": np.array([-20.0, 20.0]),
"HipExternalRotation": np.array([-20.0, 20.0]),
"HipInternalRotation": np.array([-20.0, 20.0]),
}


macros = []

for study, (primary_dof, secondary_dof) in simulation_plan.items():
    rom_primary = range_of_motion[study]
    submacros = []
    rom_secondary = np.linspace(*range_of_motion[secondary_dof], 40)
    for secondary_val in rom_secondary:
        submacros.append([
            mc.Load("EvaluateJointStrength.main.any"),
            # Set parameters for easier output

            mc.SetValue(f"Main.HumanModel.EvaluateJointStrength.Right.Leg.{study}.RangeOfMotion", rom_primary ),
            mc.SetValue(f"Main.HumanModel.EvaluateJointStrength.Right.Leg.{study}.{secondary_dof}", secondary_val),
            mc.OperationRun(f"Main.HumanModel.EvaluateJointStrength.Right.Leg.{study}.Study.InverseDynamics"),

            mc.Export(f"Main.HumanModel.EvaluateJointStrength.Right.Leg.{study}.Study.Output.JointStrength.Abscissa.JointAngle", "measurePrimaryDoF"),
            mc.Export(f"Main.HumanModel.EvaluateJointStrength.Right.Leg.{study}.Study.Output.JointStrength.JointStrength", "measureValue"),
            mc.AddToOutput("measureObject", study_map[study]),
            mc.AddToOutput("primaryDoF", dof_map[primary_dof][0]),
            mc.AddToOutput("secondaryDoF", dof_map[secondary_dof][0]),
            mc.AddToOutput("measureSecondDoF", secondary_val),
            mc.AddToOutput("measureSecondDoFSign", dof_map[secondary_dof][1]),
            mc.AddToOutput("measurePrimaryDoFSign", dof_map[primary_dof][1]),
        ])
    macros.extend(submacros)

app = AnyPyProcess(num_processes=5)
results = app.start_macro(macros[0:3])

df_pandas = results.to_dataframe(index_var="measurePrimaryDoF", exclude_task_info=True)

# Change signs of variables which are opposite to the AnyBody convention
df = pl.from_pandas(df_pandas).with_columns(
    pl.col("measureSecondDoF")*pl.col("measureSecondDoFSign").alias("measureSecondDoF"),
    pl.col("measurePrimaryDoF")*pl.col("measurePrimaryDoFSign").alias("measurePrimaryDoF"),
).drop(["measureSecondDoFSign", "measurePrimaryDoFSign"])

# df.to_parquet("joint_strength_results.parquet")

print(df)