import json
import pathlib
import os

import pytest
from crawl import _api, _globals


FAKE_SET = {
    "https://www.tutorialsteacher.com/python/python-idle",
    "https://www.python.org/downloads/",
    "https://python101.pythonlibrary.org/chapter1_idle.html",
}


mock_curriculum_data = {
    "course": "computer-science",
    "levels": [
        {
            "level": "university-year-1",
            "modules": [
                {
                    "module": "python-101",
                    "topics" : [
                        "IDLE Programming python",
                        "All About Strings python"
                   ]
                }
            ]
        }
    ]
}

mock_search_results_data = {
    "IDLE Programming python": {
        "query": "IDLE Programming python",
        "meta-data": "computer-science/university-year-1/python-101",
        "search-results": [
            "https://www.tutorialsteacher.com/python/python-idle",
            "https://www.python.org/downloads/",
        ],
        "last-discovered": -1,
    }
}

mock_fetched_data =  {
    "url": "https://www.programiz.com/python-programming/online-compiler/",
    "title": "Online Python Compiler (Interpreter)",
    "author": "www.programiz.com",
    "type": "A",
    "source": "www.programiz.com"
}

# _api.process returns a generator so we can use a list here
# to make iteration possible
mock_data_from_search_engine_scrape = [{
    "query": "I am a query",
    "meta-data": "some/fake/meta-data/path",
    "search-results": list(FAKE_SET),
    "last-discovered": -1,
}]

mock_search_res_data = {
    'All About Strings python': {'last-discovered': -1,
                              'meta-data': 'computer-science/university-year-1/python-101',
                              'query': 'All About Strings python',
                              'search-results': ['https://python101.pythonlibrary.org/chapter1_idle.html',
                                                 'https://www.tutorialsteacher.com/python/python-idle',
                                                 'https://www.python.org/downloads/']},
    'IDLE Programming python': {'last-discovered': -1,
                             'meta-data': 'computer-science/university-year-1/python-101',
                             'query': 'IDLE Programming python',
                             'search-results': ['https://python101.pythonlibrary.org/chapter1_idle.html',
                                                'https://www.tutorialsteacher.com/python/python-idle',
                                                'https://www.python.org/downloads/']}
}


def test_api_process_happy(mocker):
    mocker.patch("time.sleep", return_value=None)
    mocker.patch("random.shuffle", return_value=list(FAKE_SET))
    mocker.patch(
        "crawl._api.fetch_query", return_value=FAKE_SET)

    topic_index = 0
    expected_out = {
        "meta-data": "computer-science/university-year-1/python-101",
        "search-results": list(FAKE_SET),
        "last-discovered": -1,
    }
    for out in _api.process(mock_curriculum_data):
        expected_out["query"] = mock_curriculum_data["levels"][0]["modules"][0]["topics"][topic_index]
        assert out == expected_out
        topic_index += 1


def test_api_process_no_results(mocker):
    mocker.patch("time.sleep", return_value=None)
    mocker.patch(
        "crawl._api.fetch_query", return_value=set())

    topic_index = 0
    expected_out = {
        "meta-data": "computer-science/university-year-1/python-101",
        "search-results": [],
        "last-discovered": -1,
    }
    for out in _api.process(mock_curriculum_data):
        expected_out["query"] = mock_curriculum_data["levels"][0]["modules"][0]["topics"][topic_index]
        assert out == expected_out
        topic_index += 1


def test_course_processor_creates_correct_files(mocker, tmpdir):
    mocker.patch(
        "crawl._api.process",
        return_value=mock_data_from_search_engine_scrape
    )
    mocker.patch(
        "sylli_crawl.utils.helpers.read_json",
        return_value=mock_curriculum_data
    )
    mocker.patch.object(_globals, "SEARCH_RESULT_OUT_FOLDER", tmpdir)
    # run curriculum processor
    _api.course_processor(pathlib.Path("some/fake/path"))

    assert len(tmpdir.listdir()) == 1
    for file in tmpdir.listdir():
        # this should be the basename of the original file input into
        # course_processor
        assert file.basename == "path"
        with open(file, "r") as fd:
            actual = json.load(fd)
            assert actual == {mock_data_from_search_engine_scrape[0]["query"]: mock_data_from_search_engine_scrape[0]}


def test_api_course_processor_no_course_data(mocker):
    mocker.patch("sylli_crawl.utils.helpers.read_json", return_value=None)
    assert _api.course_processor("some/full/path") == 1


def test_api_search_res_processor_happy(mocker, tmpdir):
    mocker.patch("time.sleep", return_value=None)
    mocker.patch(
        "crawl._api.fetch_url",
        return_value=mock_fetched_data
    )
    mocker.patch(
        "crawl._api.update_save_json",
        return_value=None
    )
    mocker.patch.object(
        _globals, "RESOURCES_OUT_FOLDER", tmpdir)
    # we need to write data to the search-results dir so we
    # can avoid mocking out `read_json` as it is used in multiple
    # functions we want to test
    some_fake_file = pathlib.Path(f"{tmpdir}/test-example.json")
    with open(some_fake_file, "w") as fd:
        json.dump(mock_search_results_data, fd)

    _api.search_results_processor(some_fake_file)

    cat_path = _globals.RESOURCES_OUT_FOLDER / "computer-science/university-year-1/python-101"
    assert len(cat_path.listdir()) == 1
    for file in cat_path.listdir():
        assert f'{mock_search_results_data["IDLE Programming python"]["meta-data"]}/{mock_search_results_data["IDLE Programming python"]["query"].replace(" ", "-")}' in str(file)
        with open(file, "r") as f:
            out = json.load(f)
            # each resource file should only contain one key
            assert len(out) == 1
            for key in out.keys():
                # the input data contains two topics, output will be 2 fetched
                # resources
                assert len(out[key]) == 2
                # we just need to check the first one as any requests are
                # mocked out to return mock_fetched_data
                # this is a check to make sure the correct information is
                # written
                assert out[key][0] == mock_fetched_data


def test_end_to_end_dispatch_query(mocker, tmpdir):
    mocker.patch("time.sleep", return_value=None)
    mocker.patch("random.shuffle", return_value=list(FAKE_SET))
    mocker.patch(
        "crawl._api.fetch_query", return_value=FAKE_SET
    )
    query_dir = tmpdir.mkdir("querys")
    search_dir = tmpdir.mkdir("search-results")
    # tmpdir is a py.path.local object not pathlib.Path
    # so we need to convert
    # https://py.readthedocs.io/en/latest/path.html
    mocker.patch.object(
        _globals, "QUERY_FOLDER", pathlib.Path(query_dir)
    )
    mocker.patch.object(
        _globals, "SEARCH_RESULT_OUT_FOLDER", pathlib.Path(search_dir)
    )

    fake_resources = query_dir / "some-fake-resource.json"
    # add data
    with open(fake_resources, "w") as fd:
        json.dump(mock_curriculum_data, fd)

    
    _api.dispatch("query")
    assert len(search_dir.listdir()) == 1

    topic_list = mock_curriculum_data["levels"][0]["modules"][0]["topics"]
    for file in search_dir.listdir():
        # read contents and assert its correct
        expected_out = {
            "meta-data": "computer-science/university-year-1/python-101",
            "search-results": list(FAKE_SET),
            "last-discovered": -1,
        }
        with open(file, "r") as fd:
            actual_out = json.load(fd)
            for key, value in actual_out.items():
                # this is not fixed so we need to add it during the test
                expected_out["query"] = key
                assert value == expected_out

    # we want to make sure all the files have been processed properly
    # and not start with a `_` symbol
    assert not fake_resources.exists()
    for file in query_dir.listdir():
        assert file.basename.startswith("_")


def test_end_to_end_dispatch_search(mocker, tmpdir):
    mocker.patch("time.sleep", return_value=None)
    mocker.patch(
        "crawl._api.fetch_url", return_value=mock_fetched_data
    )

    search_dir = tmpdir.mkdir("search-results")
    res_out_folder = tmpdir.mkdir("resources")

    # tmpdir is a py.path.local object not pathlib.Path
    # so we need to convert
    # https://py.readthedocs.io/en/latest/path.html
    mocker.patch.object(
        _globals, "SEARCH_RESULT_OUT_FOLDER", pathlib.Path(search_dir)
    )
    mocker.patch.object(
        _globals, "RESOURCES_OUT_FOLDER", pathlib.Path(res_out_folder)
    )

    # write fake data to search results directory
    fake_data_path = search_dir / "test-example.json"
    with open(fake_data_path, "w") as fd:
        json.dump(mock_search_res_data, fd)

    _api.dispatch("search")

    # check correct dirs exist
    path_to_base = res_out_folder / "computer-science/university-year-1/python-101"
    assert path_to_base.check()
    # check correct number of files have been created
    assert len(path_to_base.listdir()) == len(mock_search_res_data)
    for file in path_to_base.listdir():
        with open(file, "r") as fd:
            actual_out = json.load(fd)
            # we should only have one key in this file
            assert len(actual_out) == 1
            for key in actual_out.keys():
                # there should data for each of the URLs in FAKE_SET
                assert len(actual_out[key]) == len(FAKE_SET)

    ### assertions on original "test-example.json"
    # check no extra files have been created
    assert len(search_dir.listdir()) == 1
    # check file has been renamed and starts with _
    assert not fake_data_path.exists()
    for file in search_dir.listdir():
        assert file.basename.startswith("_")
    # check counter got updated
    with open(search_dir / "_test-example.json", "r") as fd:
        actual_out = json.load(fd)
        for key in actual_out.keys():
            # counter should be 2 as that was the last index crawled
            assert actual_out[key]["last-discovered"] == 2
