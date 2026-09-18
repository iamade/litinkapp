/**
 * KAN-467: createCharacter/updateCharacter must carry the AI-Assisted voice fields
 * (accent, voice_gender, voice_characteristics) through to the API payload.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  post: vi.fn(),
  put: vi.fn(),
}));

vi.mock("../lib/api", () => ({
  apiClient: { post: mocks.post, put: mocks.put },
}));

vi.mock("../lib/videoGenerationApi", () => ({
  normalizeGenerationStatus: (status: string | null | undefined) => status ?? null,
}));

import { userService } from "./userService";

describe("userService character voice field payloads (KAN-467)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("createCharacter sends accent/voice_gender/voice_characteristics in the POST body", async () => {
    mocks.post.mockResolvedValue({ id: "char-1" });

    await userService.createCharacter("plot-1", {
      name: "Amara",
      role: "Protagonist",
      accent: "british",
      voice_gender: "female",
      voice_characteristics: "warm and friendly",
    });

    expect(mocks.post).toHaveBeenCalledTimes(1);
    const [url, body] = mocks.post.mock.calls[0];
    expect(url).toBe("/characters/plot/plot-1");
    expect(body.name).toBe("Amara");
    expect(body.accent).toBe("british");
    expect(body.voice_gender).toBe("female");
    expect(body.voice_characteristics).toBe("warm and friendly");
    expect(body.plot_overview_id).toBe("plot-1");
  });

  it("updateCharacter forwards voice fields in the PUT body", async () => {
    mocks.put.mockResolvedValue({});

    await userService.updateCharacter("char-1", {
      accent: "jamaican",
      voice_gender: "male",
    });

    expect(mocks.put).toHaveBeenCalledTimes(1);
    const [url, body] = mocks.put.mock.calls[0];
    expect(url).toBe("/characters/char-1");
    expect(body).toEqual({ accent: "jamaican", voice_gender: "male" });
  });
});
