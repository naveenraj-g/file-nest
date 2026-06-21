/**
 * Barrel export for all file domain controllers.
 *
 * @module
 */
export {
  listFilesController,
  type TListFilesControllerOutput,
} from "./listFiles.controller";

export {
  deleteFileController,
  type TDeleteFileControllerOutput,
} from "./deleteFile.controller";

export {
  getFileDownloadUrlController,
  type TGetFileDownloadUrlControllerOutput,
} from "./getFileDownloadUrl.controller";

export {
  setTagsController,
  type TSetTagsControllerOutput,
} from "./setTags.controller";

export {
  addTagsController,
  type TAddTagsControllerOutput,
} from "./addTags.controller";

export {
  updateMetadataController,
  type TUpdateMetadataControllerOutput,
} from "./updateMetadata.controller";

export {
  mergeMetadataController,
  type TMergeMetadataControllerOutput,
} from "./mergeMetadata.controller";
