from app.core.services.file import FileService


def test_save_structure_normalizes_sectioned_preview_payload():
    service = FileService()

    entries = service._iter_confirmed_structure_entries(
        [
            {
                "title": "PART ONE",
                "section_type": "part",
                "section_number": "one",
                "content_type": "chapter",
                "chapters": [
                    {
                        "title": "Chapter 1: Into Oceania",
                        "content": "Chapter one body",
                        "content_type": "chapter",
                    },
                    {
                        "title": "Chapter 2: The Room",
                        "content": "Chapter two body",
                        "content_type": "chapter",
                    },
                ],
            },
            {
                "title": "Dedication",
                "content": "For the reader",
                "content_type": "front_matter",
                "chapters": [],
            },
            {
                "title": "PART TWO",
                "section_type": "part",
                "section_number": "two",
                "content_type": "chapter",
                "chapters": [
                    {
                        "title": "Chapter 3: The Ministry",
                        "content": "Chapter three body",
                        "content_type": "chapter",
                    }
                ],
            },
            {
                "title": "Appendix",
                "content": "Appendix body",
                "content_type": "back_matter",
                "chapters": [],
            },
        ]
    )

    section_entries = [entry for entry in entries if entry["kind"] == "section"]
    chapter_entries = [entry for entry in entries if entry["kind"] == "chapter"]

    assert [entry["data"]["title"] for entry in section_entries] == [
        "PART ONE",
        "PART TWO",
    ]
    assert [entry["data"]["title"] for entry in chapter_entries] == [
        "Chapter 1: Into Oceania",
        "Chapter 2: The Room",
        "Dedication",
        "Chapter 3: The Ministry",
        "Appendix",
    ]

    part_one_key = section_entries[0]["section_key"]
    part_two_key = section_entries[1]["section_key"]
    assert chapter_entries[0]["section_key"] == part_one_key
    assert chapter_entries[1]["section_key"] == part_one_key
    assert chapter_entries[2]["section_key"] is None
    assert chapter_entries[3]["section_key"] == part_two_key
    assert chapter_entries[4]["section_key"] is None


def test_save_structure_preserves_existing_flat_section_title_payload():
    service = FileService()

    entries = service._iter_confirmed_structure_entries(
        [
            {
                "title": "Chapter 1",
                "content": "Body",
                "section_title": "PART ONE",
                "section_type": "part",
                "section_number": "one",
                "content_type": "chapter",
            },
            {
                "title": "Chapter 2",
                "content": "Body",
                "section_title": "PART ONE",
                "section_type": "part",
                "section_number": "one",
                "content_type": "chapter",
            },
        ]
    )

    assert [entry["kind"] for entry in entries] == [
        "section",
        "chapter",
        "section",
        "chapter",
    ]
    assert entries[1]["section_key"] == entries[0]["section_key"]
    assert entries[3]["section_key"] == entries[0]["section_key"]
