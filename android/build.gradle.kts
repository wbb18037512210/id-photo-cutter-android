allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}
subprojects {
    project.evaluationDependsOn(":app")
}

// Force every plugin subproject (e.g. image_gallery_saver) to compile against a
// high enough SDK. Some cached plugins declare compileSdkVersion 30, which the
// modern androidx transitive deps reject (require >= 34).
subprojects {
    try {
        afterEvaluate {
            val androidExt = extensions.findByName("android") ?: return@afterEvaluate
            try {
                val setCompile = androidExt.javaClass.methods
                    .firstOrNull { it.name == "setCompileSdkVersion" && it.parameterCount == 1 }
                setCompile?.invoke(androidExt, 36)
                val setMin = androidExt.javaClass.methods
                    .firstOrNull { it.name == "setMinSdkVersion" && it.parameterCount == 1 }
                setMin?.invoke(androidExt, 21)
            } catch (_: Throwable) {
                // best-effort; ignore reflection failures
            }
        }
    } catch (_: Throwable) {
        // afterEvaluate may throw if the project is already evaluated; ignore.
    }
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
