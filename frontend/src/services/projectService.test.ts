/**
 * KAN-147: createProjectFromUpload must carry trailer intent (output_type +
 * JSON trailer_config) on the FormData sent to /projects/upload.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  upload: vi.fn(),
}));

vi.mock("../lib/api", () => ({
  apiClient: { upload: mocks.upload },
}));

import { projectService } from "./projectService";

describe("projectService.createProjectFromUpload trailer fields (KAN-147)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.upload.mockResolvedValue({ project_id: "p-1", status: "processing" });
  });

  it("appends output_type and JSON-stringified trailer_config to the FormData", async () => {
    await projectService.createProjectFromUpload([], "entertainment", "logline", {
      content_type: "trailer_promo",
      output_type: "trailer",
      trailer_config: {
        target_duration_seconds: 90,
        tone: "epic",
        style: "cinematic",
      },
    });

    expect(mocks.upload).toHaveBeenCalledTimes(1);
    const [url, formData] = mocks.upload.mock.calls[0];
    expect(url).toBe("/projects/upload");
    expect(formData.get("output_type")).toBe("trailer");
    expect(JSON.parse(String(formData.get("trailer_config")))).toEqual({
      target_duration_seconds: 90,
      tone: "epic",
      style: "cinematic",
    });
    expect(formData.get("content_type")).toBe("trailer_promo");
  });

  it("omits output_type/trailer_config when consultationConfig has no trailer intent", async () => {
    await projectService.createProjectFromUpload([], "entertainment", "logline", {
      content_type: "single_script",
    });

    const [, formData] = mocks.upload.mock.calls[0];
    expect(formData.get("output_type")).toBeNull();
    expect(formData.get("trailer_config")).toBeNull();
  });
});
