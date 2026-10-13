/**
 * @vitest-environment jsdom
 *
 * KAN-147: AIConsultationModal must forward trailer intent (outputType +
 * trailerConfig) in the onComplete payload for trailer content types and
 * leave non-trailer payloads unchanged.
 */
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import * as matchers from "@testing-library/jest-dom/matchers";

expect.extend(matchers);

const mocks = vi.hoisted(() => ({
  upload: vi.fn(),
  post: vi.fn(),
}));

vi.mock("../../lib/api", () => ({
  apiClient: { upload: mocks.upload, post: mocks.post },
}));

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({ user: { subscription_tier: "free" } }),
}));

import { AIConsultationModal } from "./AIConsultationModal";

const makeFile = () =>
  new File(["story text"], "story.txt", { type: "text/plain" });

const chatResponse = (contentType: string) => ({
  ai_message: "Ready to create your project!",
  ready_to_proceed: true,
  project_config: {
    project_type: "entertainment",
    content_type: contentType,
    terminology: "Film",
    universe_name: "Test Universe",
  },
  messages_used: 2,
  messages_remaining: 13,
  message_limit: 15,
});

const createViaConsultation = async (
  contentType: string,
  onComplete: ReturnType<typeof vi.fn>
) => {
  mocks.post.mockResolvedValue(chatResponse(contentType));

  render(
    <AIConsultationModal
      files={[makeFile()]}
      initialPrompt="make a trailer"
      onComplete={onComplete}
      onCancel={vi.fn()}
    />
  );

  const input = await screen.findByPlaceholderText(
    "Type a message or select an option above..."
  );
  await waitFor(() => expect(input).not.toBeDisabled());
  await userEvent.type(input, "make it a trailer{enter}");

  const createButton = await screen.findByRole("button", {
    name: /create project/i,
  });
  await waitFor(() => expect(createButton).toBeEnabled());
  await userEvent.click(createButton);
};

describe("AIConsultationModal trailer intent (KAN-147)", () => {
  beforeAll(() => {
    Element.prototype.scrollIntoView = vi.fn();
  });

  beforeEach(() => {
    mocks.upload.mockResolvedValue({
      status: "completed",
      content_analysis: {
        document_type: "story",
        title: "Test Universe",
        summary: "A test story.",
        quality_assessment: "good",
      },
      file_summary: "story file",
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("trailer contentType forwards outputType=trailer + default trailerConfig in onComplete", async () => {
    const onComplete = vi.fn();
    await createViaConsultation("trailer_promo", onComplete);

    expect(onComplete).toHaveBeenCalledTimes(1);
    const payload = onComplete.mock.calls[0][0];
    expect(payload.contentType).toBe("trailer_promo");
    expect(payload.outputType).toBe("trailer");
    expect(payload.trailerConfig).toEqual({
      target_duration_seconds: 90,
      tone: "epic",
      style: "cinematic",
    });
  });

  it("non-trailer contentType payload omits outputType and trailerConfig", async () => {
    const onComplete = vi.fn();
    await createViaConsultation("single_script", onComplete);

    expect(onComplete).toHaveBeenCalledTimes(1);
    const payload = onComplete.mock.calls[0][0];
    expect(payload.contentType).toBe("single_script");
    expect(payload).not.toHaveProperty("outputType");
    expect(payload).not.toHaveProperty("trailerConfig");
  });
});
